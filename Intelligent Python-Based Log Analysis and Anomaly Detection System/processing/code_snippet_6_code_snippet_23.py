class ClusterEventAligner:
    """Aligns events across clusters for temporal analysis"""
    
    def __init__(self, temporal_correlator: TemporalCorrelator):
        self.correlator = temporal_correlator
        self.aligned_windows: Dict[str, TimeWindow] = {}  # alignment_id -> window
        self.event_alignments: Dict[str, Dict] = {}  # alignment_id -> alignment data
    
    def find_alignments(
        self,
        cluster_ids: List[str],
        lookback_seconds: int = 3600,
        min_overlap_seconds: int = 30
    ) -> List[str]:
        """Find temporal alignments between the given clusters"""
        # Get time windows for each cluster
        window_map = {}
        
        for cluster_id in cluster_ids:
            # Get meaningful time windows from correlator
            patterns = self.correlator.get_related_patterns(cluster_id)
            all_windows = self.correlator.get_aligned_time_windows(
                patterns,
                window_size_seconds=lookback_seconds
            )
            
            if cluster_id in all_windows:
                window_map[cluster_id] = all_windows[cluster_id]
        
        # Find alignments
        alignments = self.correlator.find_aligned_windows(
            window_map,
            min_overlap_seconds=min_overlap_seconds
        )
        
        alignment_ids = []
        
        for alignment in alignments:
            # Generate ID for this alignment
            alignment_id = str(uuid.uuid4())
            
            # Store the common overlap window
            common_start = datetime.fromisoformat(alignment["common_overlap"]["start"])
            common_end = datetime.fromisoformat(alignment["common_overlap"]["end"])
            self.aligned_windows[alignment_id] = TimeWindow(common_start, common_end)
            
            # Store full alignment data
            self.event_alignments[alignment_id] = alignment
            alignment_ids.append(alignment_id)
            
        return alignment_ids
    
    def analyze_aligned_events(self, alignment_id: str) -> Dict:
        """Analyze events within an aligned time window"""
        if alignment_id not in self.aligned_windows:
            return {"error": "Alignment not found"}
            
        window = self.aligned_windows[alignment_id]
        alignment = self.event_alignments[alignment_id]
        clusters = alignment["clusters"]
        
        result = {
            "alignment_id": alignment_id,
            "window": {
                "start": window.start.isoformat(),
                "end": window.end.isoformat(),
                "duration": window.duration_seconds()
            },
            "clusters": clusters,
            "events": {},
            "transitions": [],
            "potential_causality": [],
        }
        
        # Get events for each cluster in the window
        for cluster_id in clusters:
            cluster_events = self.correlator.time_series.get_window(
                f"cluster:{cluster_id}",
                window.start,
                window.end
            )
            
            # Sort by timestamp
            cluster_events.sort(key=lambda x: x[0])
            
            # Format for output
            result["events"][cluster_id] = [
                {
                    "timestamp": ts.isoformat(),
                    "fingerprint": data.get("fingerprint"),
                    "anomaly_type": data.get("anomaly_type"),
                    "details": data.get("details", {})
                }
                for ts, data in cluster_events
            ]
            
        # Analyze causal transitions between all cluster pairs
        for i in range(len(clusters)):
            for j in range(i+1, len(clusters)):
                source_cluster = clusters[i]
                target_cluster = clusters[j]
                
                # Check transitions in both directions
                forward_transitions = self.correlator.analyze_causal_field_transitions(
                    source_cluster, target_cluster, window
                )
                
                backward_transitions = self.correlator.analyze_causal_field_transitions(
                    target_cluster, source_cluster, window
                )
                
                # Add to results
                for transition in forward_transitions:
                    transition["source_cluster"] = source_cluster
                    transition["target_cluster"] = target_cluster
                    result["transitions"].append(transition)
                    
                for transition in backward_transitions:
                    transition["source_cluster"] = target_cluster
                    transition["target_cluster"] = source_cluster
                    result["transitions"].append(transition)
                    
                # Determine potential causality
                if forward_transitions and not backward_transitions:
                    result["potential_causality"].append({
                        "likely_cause": source_cluster,
                        "likely_effect": target_cluster,
                        "confidence": max(t["confidence"] for t in forward_transitions),
                        "transitions": len(forward_transitions)
                    })
                elif backward_transitions and not forward_transitions:
                    result["potential_causality"].append({
                        "likely_cause": target_cluster,
                        "likely_effect": source_cluster,
                        "confidence": max(t["confidence"] for t in backward_transitions),
                        "transitions": len(backward_transitions)
                    })
                elif forward_transitions and backward_transitions:
                    # Bidirectional, determine which is stronger
                    forward_strength = sum(t["confidence"] for t in forward_transitions)
                    backward_strength = sum(t["confidence"] for t in backward_transitions)
                    
                    if forward_strength > backward_strength * 1.5:  # Significantly stronger
                        result["potential_causality"].append({
                            "likely_cause": source_cluster,
                            "likely_effect": target_cluster,
                            "confidence": forward_strength / (forward_strength + backward_strength),
                            "transitions": len(forward_transitions),
                            "bidirectional": True,
                            "dominance": "forward"
                        })
                    elif backward_strength > forward_strength * 1.5:
                        result["potential_causality"].append({
                            "likely_cause": target_cluster,
                            "likely_effect": source_cluster,
                            "confidence": backward_strength / (forward_strength + backward_strength),
                            "transitions": len(backward_transitions),
                            "bidirectional": True,
                            "dominance": "backward"
                        })
                    else:
                        # No clear causality
                        result["potential_causality"].append({
                            "mutual_interaction": True,
                            "clusters": [source_cluster, target_cluster],
                            "forward_transitions": len(forward_transitions),
                            "backward_transitions": len(backward_transitions),
                            "balance": forward_strength / (forward_strength + backward_strength)
                        })
        
        # Sort transitions by confidence
        result["transitions"].sort(key=lambda x: x["confidence"], reverse=True)
        
        return result