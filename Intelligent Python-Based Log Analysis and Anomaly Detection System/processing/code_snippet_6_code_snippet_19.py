class Anomaly:
    def __init__(self, id='anomaly-001', message='Test anomaly'):
        self.id = id
        self.message = message
class StakeholderRegistry:
    def get_contacts(self, alert_type):
        return ["oncall@example.com"]
class NotificationGateway:
    def send(self, recipients, message):
        print(f"Notification sent to {recipients}: {message}")
class AlertTracker:
    def record(self, alert):
        print(f"Tracking alert: {alert}")
class EscalationRule:
    def __init__(self, rule_id="rule-001"):
        self.rule_id = rule_id
class IncidentManager:
    def create(self, details):
        print(f"Incident created with details: {details}")
from typing import Optional
from typing import List, Dict
from datetime import datetime
class OptimizedEscalationPolicyEngine:
    """High-performance escalation policy engine for high-volume alerts"""
    
    def __init__(
        self,
        stakeholder_registry: StakeholderRegistry,
        notification_gateway: NotificationGateway,
        alert_tracker: AlertTracker,
        incident_manager: IncidentManager,
        cache_ttl_seconds: int = 300,
        max_cache_entries: int = 10000
    ):
        self.stakeholder_registry = stakeholder_registry
        self.notification_gateway = notification_gateway
        self.alert_tracker = alert_tracker
        self.incident_manager = incident_manager
        
        # Core rule storage structures
        self.rules_by_level: Dict[EscalationLevel, List[EscalationRule]] = {
            level: [] for level in EscalationLevel
        }
        self.service_specific_rules: Dict[str, List[EscalationRule]] = {}
        self.risk_scorer = RiskScorer()
        
        # Optimization components
        self.cache = EscalationDecisionCache(
            default_ttl_seconds=cache_ttl_seconds,
            max_entries=max_cache_entries
        )
        self.debouncer = TriggerDebouncer()
        self.rule_optimizer = RuleEvaluationOptimizer(self)
        self.batch_engine = BatchedEvaluationEngine(
            self, self.cache, self.debouncer, self.rule_optimizer
        )
        
        # Priority queue for scheduled evaluations
        self.evaluation_queue = []
        self.last_queue_check = time.time()
        
        # Dynamic TTL settings
        self.ttl_by_type: Dict[AnomalyType, int] = {
            AnomalyType.SECURITY: 900,        # 15 minutes for security issues
            AnomalyType.AVAILABILITY: 600,    # 10 minutes for availability
            AnomalyType.PERFORMANCE: 1800,    # 30 minutes for performance
            AnomalyType.DATA_INTEGRITY: 1200, # 20 minutes for data integrity
            AnomalyType.CONFIGURATION: 3600   # 1 hour for configuration
        }
        
    async def queue_anomaly_for_evaluation(self, anomaly: Anomaly) -> None:
        """Add an anomaly to the batched evaluation queue"""
        fingerprint = anomaly.fingerprint
        self.batch_engine.queue_anomaly(anomaly, fingerprint)
        
    def add_rule(self, rule: EscalationRule, service: Optional[str] = None) -> None:
        """Add an escalation rule, optionally for a specific service"""
        if service:
            if service not in self.service_specific_rules:
                self.service_specific_rules[service] = []
            self.service_specific_rules[service].append(rule)
        else:
            level = EscalationLevel.INITIAL
            if rule.next_level:
                level = rule.next_level
            self.rules_by_level[level].append(rule)
            
        # Rebuild rule indexes
        self.rule_optimizer._build_indexes()
        
        # Invalidate cache for affected service
        if service:
            # Identify fingerprints for this service
            service_fingerprints = [
                fp for fp, alert in self.alert_tracker.alerts.items()
                if alert["service_name"] == service
            ]
            
            # Invalidate cache for these fingerprints
            for fp in service_fingerprints:
                self.cache.invalidate(fingerprint=fp)
    
    async def check_for_escalations(self) -> List[Dict]:
        """
        Scan for alerts that need escalation based on time thresholds
        This would typically be called by a scheduled task
        """
        now = time.time()
        
        # Process any pending batched anomalies first
        if self.batch_engine.pending_anomalies:
            self.batch_engine.process_batch()
            
        # Check evaluation queue
        due_fingerprints = []
        while self.evaluation_queue and self.evaluation_queue[0][0] <= now:
            # Pop items due for evaluation
            _, fingerprint = heapq.heappop(self.evaluation_queue)
            due_fingerprints.append(fingerprint)
            
        # Process due fingerprints
        escalation_actions = []
        for fingerprint in due_fingerprints:
            # Skip if alert no longer exists or is resolved
            if (fingerprint not in self.alert_tracker.alerts or
                self.alert_tracker.alerts[fingerprint]["state"] == AlertState.RESOLVED):
                continue
                
            # Skip if debounced
            if not self.debouncer.should_evaluate(fingerprint):
                continue
                
            # Get alert details
            alert = self.alert_tracker.alerts[fingerprint]
            anomaly = alert["last_anomaly"]
            current_level = alert["current_escalation_level"]
            
            # Check cache
            cached_escalations = {}
            for rule in self.rules_by_level[current_level]:
                cached_result = self.cache.get(fingerprint, rule.id, current_level)
                if cached_result:
                    cached_escalations[rule.id] = cached_result
                    
            # If we have cached results, use them
            if cached_escalations:
                # Use the first available cached result
                rule_id, escalation = next(iter(cached_escalations.items()))
                escalation_actions.append(escalation)
                continue
                
            # Get applicable rules the optimized way
            rules = self.rule_optimizer.get_applicable_rules_optimized(
                anomaly, current_level
            )
            
            if not rules:
                continue
                
            # Use the first applicable rule
            rule = rules[0]
            
            # Calculate dynamic TTL for this anomaly type
            ttl = self.ttl_by_type.get(anomaly.anomaly_type, 300)
            
            # Perform the escalation
            escalation = await self._perform_escalation(fingerprint, anomaly, rule)
            if escalation:
                # Cache with dynamic TTL
                self.cache.set(fingerprint, rule.id, current_level, escalation, ttl_seconds=ttl)
                escalation_actions.append(escalation)
                
                # Record that an action was taken
                self.debouncer.record_action_taken(fingerprint)
                
        return escalation_actions
    
    def schedule_next_evaluation(self, 
                               fingerprint: str, 
                               next_time: datetime) -> None:
        """Schedule an alert for future evaluation"""
        # Convert datetime to timestamp
        next_timestamp = next_time.timestamp()
        
        # Add to priority queue
        heapq.heappush(self.evaluation_queue, (next_timestamp, fingerprint))
    
    def get_optimization_stats(self) -> Dict:
        """Get statistics about optimization effectiveness"""
        stats = {
            "cache": self.cache.get_stats(),
            "debouncer": self.debouncer.get_stats(),
            "batching": self.batch_engine.get_stats(),
            "rules": {
                "total_rules": sum(len(rules) for rules in self.rules_by_level.values()) +
                            sum(len(rules) for rules in self.service_specific_rules.values()),
                "rule_performance": self.rule_optimizer.get_rule_performance_stats(),
            },
            "queue": {
                "scheduled_evaluations": len(self.evaluation_queue)
            }
        }
        
        return stats