class CausalGraphBuilder:
    """Builds and analyzes causal graphs from temporal correlations"""
    
    def __init__(self, temporal_correlator: TemporalCorrelator):
        self.correlator = temporal_correlator
        self.known_causes: Dict[str, List[Dict]] = {}  # service -> known causes
        self.propagation_patterns: Dict[str, nx.DiGraph] = {}  # pattern_id -> graph
    
    def build_causal_graph_for_incident(
        self,
        incident_cluster_ids: List[str],
        lookback_seconds: int = 3600
    ) -> nx.DiGraph:
        """Build a causal graph for an incident involving multiple clusters"""
        G = nx.DiGraph()
        
        # Add each cluster as a node
        for cluster_id in incident_cluster_ids:
            cluster = self.correlator.cluster_manager.get_cluster(cluster_id)
            if not cluster:
                continue
                
            G.add_node(
                cluster_id,
                services=list(cluster.services),
                anomaly_count=cluster.anomaly_count,
                creation_time=datetime.fromtimestamp(cluster.creation_time)
            )
            
        # Add causal edges from temporal correlator
        for i in range(len(incident_cluster_ids)):
            source_id = incident_cluster_ids[i]
            
            # Get root cause candidates for this cluster
            root_causes = self.correlator.get_root_cause_candidates(source_id)
            
            for cause in root_causes:
                cause_id = cause["cluster_id"]
                
                # Skip if not part of our incident clusters
                if cause_id not in incident_cluster_ids:
                    continue
                    
                # Add causal edge
                G.add_edge(
                    cause_id,
                    source_id,
                    confidence=cause["confidence"],
                    causal_distance=cause.get("causal_distance", 1)
                )
                
            # Also analyze time-aligned events
            for j in range(len(incident_cluster_ids)):
                if i == j:
                    continue
                    
                target_id = incident_cluster_ids[j]
                
                # Analyze causal field transitions
                transitions = self.correlator.analyze_causal_field_transitions(
                    source_id, target_id)
                
                if transitions:
                    # Calculate aggregate confidence
                    aggregate_confidence = sum(t["confidence"] for t in transitions) / len(transitions)
                    max_confidence = max(t["confidence"] for t in transitions)
                    
                    # Only add edge if reasonably confident
                    if max_confidence >= 0.6:
                        if G.has_edge(source_id, target_id):
                            # Update existing edge
                            old_confidence = G.edges[source_id, target_id]["confidence"]
                            G.edges[source_id, target_id]["confidence"] = max(old_confidence, max_confidence)
                            G.edges[source_id, target_id]["transitions"] = transitions
                        else:
                            # Add new edge
                            G.add_edge(
                                source_id,
                                target_id,
                                confidence=max_confidence,
                                transitions=transitions,
                                transition_count=len(transitions),
                                aggregate_confidence=aggregate_confidence
                            )
        
        # Add timing information
        self._add_timing_information(G, incident_cluster_ids)
        
        # Add service topology information
        self._enhance_with_service_topology(G)
        
        return G
    
    def _add_timing_information(
        self, 
        graph: nx.DiGraph, 
        cluster_ids: List[str]
    ) -> None:
        """Add timing information to causal graph"""
        # Get creation times for all clusters
        creation_times = {}
        
        for cluster_id in cluster_ids:
            cluster = self.correlator.cluster_manager.get_cluster(cluster_id)
            if cluster:
                creation_times[cluster_id] = cluster.creation_time
        
        # Sort clusters by creation time
        sorted_clusters = sorted(
            [(cluster_id, time) for cluster_id, time in creation_times.items()],
            key=lambda x: x[1]
        )
        
        # Add timing attributes to nodes
        for i, (cluster_id, time) in enumerate(sorted_clusters):
            graph.nodes[cluster_id]["temporal_order"] = i
            graph.nodes[cluster_id]["creation_time"] = time
            
            if i > 0:
                graph.nodes[cluster_id]["time_since_first"] = time - sorted_clusters[0][1]
    
    def _enhance_with_service_topology(self, graph: nx.DiGraph) -> None:
        """Enhance causal graph with service topology information"""
        # Get all services involved
        services = set()
        for cluster_id in graph.nodes():
            services.update(graph.nodes[cluster_id].get("services", []))
            
        # Check if any services have known dependency relationships
        service_graph = self.correlator.service_graph
        
        for source, target in list(graph.edges()):
            # Get services for source and target
            source_services = graph.nodes[source].get("services", [])
            target_services = graph.nodes[target].get("services", [])
            
            # Check if services have topology relationship
            service_paths = []
            for s_service in source_services:
                for t_service in target_services:
                    if (s_service in service_graph and 
                        t_service in service_graph):
                        try:
                            paths = list(nx.all_simple_paths(
                                service_graph,
                                s_service,
                                t_service,
                                cutoff=2
                            ))
                            service_paths.extend(paths)
                        except nx.NetworkXNoPath:
                            pass
                            
            if service_paths:
                graph.edges[source, target]["topology_supported"] = True
                graph.edges[source, target]["service_paths"] = service_paths
                
                # Boost confidence if topology supports the causal link
                if "confidence" in graph.edges[source, target]:
                    graph.edges[source, target]["confidence"] = min(
                        1.0,
                        graph.edges[source, target]["confidence"] * 1.2
                    )
            else:
                graph.edges[source, target]["topology_supported"] = False
    
    def identify_root_causes(self, causal_graph: nx.DiGraph) -> List[Dict]:
        """Identify potential root causes from a causal graph"""
        if not causal_graph.nodes():
            return []
            
        # Calculate metrics for each node
        metrics = {}
        
        for node in causal_graph.nodes():
            # In-degree and out-degree
            in_degree = causal_graph.in_degree(node)
            out_degree = causal_graph.out_degree(node)
            
            # A root cause should have low in-degree and high out-degree
            if in_degree == 0 and out_degree > 0:
                # Pure source - highest priority
                role = "source"
                score = out_degree * 2
            elif in_degree < out_degree:
                # More outgoing than incoming - potential source
                role = "amplifier"
                score = out_degree - in_degree
            elif in_degree > out_degree and out_degree == 0:
                # Pure sink
                role = "sink"
                score = 0
            else:
                # Intermediate node
                role = "intermediate"
                score = out_degree / (in_degree + 1)
                
            # Adjust by temporal order if available
            temporal_order = causal_graph.nodes[node].get("temporal_order")
            if temporal_order is not None:
                # Earlier nodes are more likely to be root causes
                temporal_factor = 1.0 - (temporal_order / max(len(causal_graph.nodes()), 1))
                score *= (1.0 + temporal_factor)
                
            # Store metrics
            metrics[node] = {
                "in_degree": in_degree,
                "out_degree": out_degree,
                "role": role,
                "score": score,
                "temporal_order": temporal_order
            }
        
        # Sort nodes by score
        sorted_nodes = sorted(
            [(node, data) for node, data in metrics.items()],
            key=lambda x: x[1]["score"],
            reverse=True
        )
        
        # Format results
        results = []
        
        for node, data in sorted_nodes:
            # Get cluster information
            cluster = self.correlator.cluster_manager.get_cluster(node)
            
            result = {
                "cluster_id": node,
                "services": causal_graph.nodes[node].get("services", []),
                "role": data["role"],
                "score": data["score"],
                "in_degree": data["in_degree"],
                "out_degree": data["out_degree"],
                "temporal_order": data["temporal_order"]
            }
            
            if cluster:
                result["anomaly_count"] = cluster.anomaly_count
                
            if data["role"] in ["source", "amplifier"]:
                # For potential root causes, add effects
                successors = list(causal_graph.successors(node))
                result["affects"] = successors
                result["affected_services"] = set()
                
                for succ in successors:
                    result["affected_services"].update(
                        causal_graph.nodes[succ].get("services", [])
                    )
                    
                result["affected_services"] = list(result["affected_services"])
                
            results.append(result)
            
        return results
    
    def find_propagation_pattern(
        self, 
        causal_graph: nx.DiGraph
    ) -> Optional[Dict]:
        """Identify the propagation pattern in a causal graph"""
        if not causal_graph.nodes():
            return None
            
        # Calculate graph metrics
        metrics = {
            "node_count": len(causal_graph.nodes()),
            "edge_count": len(causal_graph.edges()),
            "density": nx.density(causal_graph),
            "is_tree": nx.is_tree(causal_graph.to_undirected()) if causal_graph.nodes() else False
        }
        
        # Try to determine the pattern
        pattern = None
        confidence = 0.0
        
        if metrics["is_tree"]:
            # Identify the root
            potential_roots = [
                node for node in causal_graph.nodes()
                if causal_graph.in_degree(node) == 0 and causal_graph.out_degree(node) > 0
            ]
            
            if len(potential_roots) == 1:
                # Single root with tree structure - cascade pattern
                root = potential_roots[0]
                depth = self._get_max_path_length(causal_graph, root)
                
                if depth >= 3:
                    pattern = "cascade"
                    confidence = 0.9
                else:
                    pattern = "star"
                    confidence = 0.8
            elif len(potential_roots) > 1:
                # Multiple roots - convergent pattern
                pattern = "convergent"
                confidence = 0.7
            else:
                # No clear root but still a tree - strange
                pattern = "complex"
                confidence = 0.5
        elif metrics["density"] > 0.7:
            # Very dense graph - mutual interaction
            pattern = "mutual"
            confidence = 0.8
        elif self._has_cycles(causal_graph):
            # Contains cycles - feedback pattern
            pattern = "feedback"
            confidence = 0.7
        else:
            # General DAG
            pattern = "complex"
            confidence = 0.6
            
        return {
            "pattern": pattern,
            "confidence": confidence,
            "metrics": metrics
        }
    
    def _get_max_path_length(self, graph: nx.DiGraph, source: str) -> int:
        """Get maximum path length from source to any node"""
        try:
            paths = nx.single_source_shortest_path_length(graph, source)
            return max(paths.values()) if paths else 0
        except:
            return 0
            
    def _has_cycles(self, graph: nx.DiGraph) -> bool:
        """Check if graph has cycles"""
        try:
            nx.find_cycle(graph)
            return True
        except nx.NetworkXNoCycle:
            return False