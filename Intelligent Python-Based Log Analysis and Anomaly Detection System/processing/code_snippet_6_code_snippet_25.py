class TemporallyAwareEscalationEngine(ClusterAwareEscalationEngine):
    """Escalation engine that uses temporal correlation for smarter decisions"""
    
    def __init__(
        self,
        stakeholder_registry: StakeholderRegistry,
        notification_gateway: NotificationGateway,
        alert_tracker: AlertTracker,
        incident_manager: IncidentManager,
        cache_ttl_seconds: int = 300,
        max_cache_entries: int = 10000,
        cluster_similarity_threshold: float = 0.7
    ):
        super().__init__(
            stakeholder_registry,
            notification_gateway,
            alert_tracker,
            incident_manager,
            cache_ttl_seconds,
            max_cache_entries,
            cluster_similarity_threshold
        )
        
        # Temporal correlation components
        self.temporal_correlator = TemporalCorrelator(self.cluster_manager)
        self.causal_graph_builder = CausalGraphBuilder(self.temporal_correlator)
        self.event_aligner = ClusterEventAligner(self.temporal_correlator)
        
        # Track potential incident correlations
        self.potential_incidents: Dict[str, Dict] = {}  # incident_id -> incident data
    
    async def queue_anomaly_for_evaluation(self, anomaly: Anomaly) -> Dict:
        """Add an anomaly to the evaluation queue with temporal correlation"""
        # First, standard cluster processing
        cluster_result = await super().queue_anomaly_for_evaluation(anomaly)
        
        # Then, process through temporal correlator
        correlation_result = self.temporal_correlator.process_anomaly(anomaly)
        
        # Combine results
        result = {
            **cluster_result,
            "temporal_correlation": correlation_result
        }
        
        # If patterns were detected, update escalation logic
        if correlation_result.get("patterns"):
            await self._handle_temporal_patterns(
                anomaly, 
                cluster_result["cluster_id"],
                correlation_result["patterns"]
            )
            
        return result
    
    async def _handle_temporal_patterns(
        self,
        anomaly: Anomaly,
        cluster_id: str,
        patterns: List[Dict]
    ) -> None:
        """Handle detected temporal patterns for escalation"""
        # Check if any pattern indicates a potential incident
        incident_patterns = [
            p for p in patterns
            if p["pattern_type"] in ["CAUSAL_CHAIN", "PRECURSOR"] 
            and len(p["source_clusters"]) >= 3
        ]
        
        if not incident_patterns:
            return
            
        # This might be part of a larger incident
        for pattern in incident_patterns:
            # Generate a unique ID for this correlated incident
            incident_key = ":".join(sorted(pattern["source_clusters"]))
            incident_id = f"corr-{hashlib.md5(incident_key.encode()).hexdigest()[:8]}"
            
            # Check if we're already tracking this potential incident
            if incident_id in self.potential_incidents:
                # Update existing potential incident
                self.potential_incidents[incident_id]["cluster_ids"].add(cluster_id)
                self.potential_incidents[incident_id]["anomalies"].append(anomaly.fingerprint)
                self.potential_incidents[incident_id]["last_update"] = datetime.now()
            else:
                # Create new potential incident
                self.potential_incidents[incident_id] = {
                    "incident_id": incident_id,
                    "pattern_id": pattern["id"],
                    "pattern_type": pattern["pattern_type"],
                    "cluster_ids": set(pattern["source_clusters"]),
                    "anomalies": [anomaly.fingerprint],
                    "first_seen": datetime.now(),
                    "last_update": datetime.now(),
                    "escalated": False
                }
            
            # Check if we need to escalate this correlated incident
            if len(self.potential_incidents[incident_id]["cluster_ids"]) >= 3 and not self.potential_incidents[incident_id]["escalated"]:
                await self._escalate_correlated_incident(incident_id)
    
    async def _escalate_correlated_incident(self, incident_id: str) -> Dict:
        """Escalate a correlated incident with causal information"""
        if incident_id not in self.potential_incidents:
            return {"status": "error", "message": "Incident not found"}
            
        incident = self.potential_incidents[incident_id]
        
        # Build causal graph
        cluster_ids = list(incident["cluster_ids"])
        causal_graph = self.causal_graph_builder.build_causal_graph_for_incident(
            cluster_ids
        )
        
        # Identify root causes
        root_causes = self.causal_graph_builder.identify_root_causes(causal_graph)
        
        # Identify propagation pattern
        propagation = self.causal_graph_builder.find_propagation_pattern(
            causal_graph
        )
        
        # Get a representative anomaly (preferably from root cause)
        representative_anomaly = None
        if root_causes:
            root_cluster = self.cluster_manager.get_cluster(root_causes[0]["cluster_id"])
            if root_cluster and root_cluster.member_fingerprints:
                root_fp = root_cluster.member_fingerprints[0]
                if root_fp in self.alert_tracker.alerts:
                    representative_anomaly = self.alert_tracker.alerts[root_fp]["last_anomaly"]
                    
        # Fallback to any anomaly if needed
        if not representative_anomaly and incident["anomalies"]:
            fp = incident["anomalies"][0]
            if fp in self.alert_tracker.alerts:
                representative_anomaly = self.alert_tracker.alerts[fp]["last_anomaly"]
                
        if not representative_anomaly:
            return {"status": "error", "message": "No representative anomaly found"}
                
        # Enhance anomaly with correlation data
        correlation_details = {
            "is_correlated_incident": True,
            "correlated_incident_id": incident_id,
            "cluster_count": len(incident["cluster_ids"]),
            "anomaly_count": len(incident["anomalies"]),
            "root_causes": root_causes[:3] if root_causes else [],
            "propagation_pattern": propagation["pattern"] if propagation else "unknown",
            "affected_services": set()
        }
        
        # Collect all affected services
        for cid in incident["cluster_ids"]:
            cluster = self.cluster_manager.get_cluster(cid)
            if cluster:
                correlation_details["affected_services"].update(cluster.services)
                
        correlation_details["affected_services"] = list(correlation_details["affected_services"])
        
        # Merge with existing details
        representative_anomaly.details.update(correlation_details)
        
        # Use higher escalation level for correlated incidents
        escalation_level = EscalationLevel.INCIDENT
        
        # Find a rule for this level
        applicable_rules = []
        for rule in self.rules_by_level.get(escalation_level, []):
            if self.rule_optimizer.rule_predicates[rule.id](representative_anomaly, escalation_level):
                applicable_rules.append(rule)
                
        if not applicable_rules:
            # Fallback to management level
            escalation_level = EscalationLevel.MANAGEMENT
            for rule in self.rules_by_level.get(escalation_level, []):
                if self.rule_optimizer.rule_predicates[rule.id](representative_anomaly, escalation_level):
                    applicable_rules.append(rule)
                    
        if not applicable_rules:
            return {"status": "error", "message": "No applicable rules found"}
            
        # Perform escalation
        result = await self._perform_escalation(
            representative_anomaly.fingerprint, 
            representative_anomaly, 
            applicable_rules[0]
        )
        
        # Mark as escalated
        incident["escalated"] = True
        incident["escalation_time"] = datetime.now()
        incident["escalation_level"] = escalation_level.name
        incident["escalation_result"] = result
        
        # Create an actual incident
        real_incident_id = self.incident_manager.create_incident(
            representative_anomaly,
            representative_anomaly.fingerprint,
            escalation_level
        )
        
        if real_incident_id:
            incident["real_incident_id"] = real_incident_id
            
        return {
            "status": "escalated",
            "incident_id": incident_id,
            "real_incident_id": real_incident_id,
            "escalation": result,
            "root_causes": root_causes[:3] if root_causes else [],
            "propagation_pattern": propagation
        }
    
    async def check_for_correlated_escalations(self) -> List[Dict]:
        """Check for potential correlated incidents that need escalation"""
        results = []
        now = datetime.now()
        
        for incident_id, incident in self.potential_incidents.items():
            # Skip already escalated incidents
            if incident["escalated"]:
                continue
                
            # Check if it's been active long enough
            time_since_first = (now - incident["first_seen"]).total_seconds()
            if time_since_first < 300:  # 5 minute minimum threshold
                continue
                
            # Check if enough clusters are involved
            if len(incident["cluster_ids"]) < 3:
                continue
                
            # Escalate this correlated incident
            escalation_result = await self._escalate_correlated_incident(incident_id)
            results.append(escalation_result)
            
        return results