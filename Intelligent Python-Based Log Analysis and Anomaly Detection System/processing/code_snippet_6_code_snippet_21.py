class ClusterAwareEscalationEngine(OptimizedEscalationPolicyEngine):
    """Escalation engine with awareness of anomaly clusters"""
    
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
            max_cache_entries
        )
        
        # Cluster management
        self.cluster_manager = ClusterManager(
            similarity_threshold=cluster_similarity_threshold
        )
        
        # Track cluster notifications to prevent duplicates
        self.cluster_notifications: Dict[str, List[Dict]] = {}  # cluster_id -> notifications
        
        # Cluster escalation thresholds
        self.cluster_size_thresholds: Dict[EscalationLevel, int] = {
            EscalationLevel.INITIAL: 1,     # Single alert
            EscalationLevel.TEAM_WIDE: 5,   # Small cluster
            EscalationLevel.MANAGEMENT: 20, # Medium cluster
            EscalationLevel.INCIDENT: 50,   # Large cluster
            EscalationLevel.EXECUTIVE: 100  # Critical mass
        }
        
    async def queue_anomaly_for_evaluation(self, anomaly: Anomaly) -> Dict:
        """Add an anomaly to the evaluation queue with cluster awareness"""
        # Process through cluster manager first
        cluster_id = self.cluster_manager.process_anomaly(anomaly)
        cluster = self.cluster_manager.get_cluster(cluster_id)
        
        result = {
            "fingerprint": anomaly.fingerprint,
            "cluster_id": cluster_id,
            "cluster_size": cluster.get_size()
        }
        
        # Check if cluster has crossed a threshold
        if self._should_evaluate_cluster(cluster):
            # Process immediately if threshold crossed
            evaluation_result = await self._evaluate_cluster(cluster)
            result["evaluation"] = evaluation_result
        else:
            # Otherwise add to batch for normal processing
            self.batch_engine.queue_anomaly(anomaly, anomaly.fingerprint)
            
        return result
        
    def _should_evaluate_cluster(self, cluster: AnomalyCluster) -> bool:
        """Determine if a cluster should be evaluated immediately"""
        # Check size thresholds
        cluster_size = cluster.get_size()
        
        # Get current highest threshold crossed
        current_level = EscalationLevel.INITIAL
        for level, threshold in self.cluster_size_thresholds.items():
            if cluster_size >= threshold:
                if level.value > current_level.value:
                    current_level = level
        
        # If cluster already evaluated at this level, skip
        if cluster.evaluation_count > 0:
            # Look up previous notifications
            previous_level = EscalationLevel.INITIAL
            if cluster.cluster_id in self.cluster_notifications:
                for notification in self.cluster_notifications[cluster.cluster_id]:
                    if notification["level"].value > previous_level.value:
                        previous_level = notification["level"]
                        
            # Only re-evaluate if we've crossed a higher threshold
            if current_level.value <= previous_level.value:
                return False
                
        # Evaluate if we're at MANAGEMENT or higher level
        return current_level.value >= EscalationLevel.MANAGEMENT.value
    
    async def _evaluate_cluster(self, cluster: AnomalyCluster) -> Dict:
        """Evaluate a cluster for escalation"""
        # Get representative anomaly
        rep_fingerprint = cluster.representative_fingerprint
        if rep_fingerprint not in self.alert_tracker.alerts:
            # Something's wrong, cluster references non-existent alert
            return {"status": "error", "message": "Representative fingerprint not found"}
            
        alert = self.alert_tracker.alerts[rep_fingerprint]
        anomaly = alert["last_anomaly"]
        
        # Determine appropriate escalation level based on size
        cluster_size = cluster.get_size()
        escalation_level = EscalationLevel.INITIAL
        
        for level, threshold in self.cluster_size_thresholds.items():
            if cluster_size >= threshold:
                if level.value > escalation_level.value:
                    escalation_level = level
        
        # Find rule for this level
        rules = self.rules_by_level.get(escalation_level, [])
        if not rules:
            return {"status": "no_rules", "cluster_id": cluster.cluster_id}
            
        # Use first applicable rule
        applicable_rule = None
        for rule in rules:
            if self.rule_optimizer.rule_predicates[rule.id](anomaly, escalation_level):
                applicable_rule = rule
                break
                
        if not applicable_rule:
            return {"status": "no_applicable_rules", "cluster_id": cluster.cluster_id}
            
        # Enhance anomaly with cluster information
        cluster_details = {
            "cluster_id": cluster.cluster_id,
            "cluster_size": cluster_size,
            "cluster_services": list(cluster.services),
            "cluster_age_seconds": cluster.get_age(),
            "is_cluster_notification": True
        }
        
        # Merge with existing details
        anomaly.details.update(cluster_details)
        
        # Perform escalation
        result = await self._perform_escalation(rep_fingerprint, anomaly, applicable_rule)
        
        # Record cluster evaluation
        self.cluster_manager.mark_cluster_processed(cluster.cluster_id)
        
        # Record notification
        if cluster.cluster_id not in self.cluster_notifications:
            self.cluster_notifications[cluster.cluster_id] = []
            
        self.cluster_notifications[cluster.cluster_id].append({
            "timestamp": datetime.now(),
            "level": escalation_level,
            "rule_id": applicable_rule.id,
            "stakeholders": result.get("notified_stakeholders", [])
        })
        
        return {
            "status": "escalated",
            "cluster_id": cluster.cluster_id, 
            "level": escalation_level.name,
            "escalation": result
        }
    
    def get_cluster_stats(self) -> Dict:
        """Get statistics about cluster management"""
        active_clusters = sum(1 for c in self.cluster_manager.clusters.values() if c.is_active)
        
        # Calculate distribution of cluster sizes
        size_distribution = {}
        for cluster in self.cluster_manager.clusters.values():
            size = cluster.get_size()
            size_category = "1"
            if size >= 100:
                size_category = "100+"
            elif size >= 50:
                size_category = "50-99"
            elif size >= 20:
                size_category = "20-49"
            elif size >= 5:
                size_category = "5-19"
            elif size > 1:
                size_category = "2-4"
                
            if size_category not in size_distribution:
                size_distribution[size_category] = 0
            size_distribution[size_category] += 1
            
        return {
            "total_clusters": len(self.cluster_manager.clusters),
            "active_clusters": active_clusters,
            "total_fingerprints_clustered": len(self.cluster_manager.fingerprint_to_cluster),
            "size_distribution": size_distribution,
            "notifications": {
                "cluster_notifications": sum(len(n) for n in self.cluster_notifications.values())
            }
        }