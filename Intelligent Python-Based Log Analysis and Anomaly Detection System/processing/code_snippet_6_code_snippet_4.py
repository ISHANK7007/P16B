class EnhancedRoutingOrchestrator(RoutingOrchestrator):
    """Enhanced orchestrator with escalation policy integration"""
    
    def __init__(
        self, 
        stakeholder_registry: StakeholderRegistry,
        notification_gateway: NotificationGateway,
        risk_scorer: RiskScorer,
        alert_tracker: AlertTracker,
        escalation_engine: EscalationPolicyEngine
    ):
        super().__init__(stakeholder_registry, notification_gateway, risk_scorer)
        self.alert_tracker = alert_tracker
        self.escalation_engine = escalation_engine
        
    async def route_anomaly(self, anomaly: Anomaly) -> Dict[str, Any]:
        """Route an anomaly, with fingerprint tracking for escalation"""
        # Check if this is a known fingerprint
        if self.alert_tracker.alerts.get(anomaly.fingerprint, None):
            # Check if it's suppressed
            if self.alert_tracker.is_suppressed(anomaly.fingerprint):
                return {"status": "suppressed", "fingerprint": anomaly.fingerprint}
            
            # This is a repeat alert - might need escalation
            existing_alert = self.alert_tracker.alerts[anomaly.fingerprint]
            
            # If this alert is already at a higher escalation level, maintain that
            if existing_alert["current_escalation_level"] != EscalationLevel.INITIAL:
                # Get applicable escalation rule
                rules = self.escalation_engine.get_applicable_rules(
                    anomaly, 
                    existing_alert["current_escalation_level"]
                )
                
                if rules:
                    # Re-notify based on the current escalation rule
                    escalation_result = await self.escalation_engine._perform_escalation(
                        anomaly.fingerprint, anomaly, rules[0]
                    )
                    return {
                        "status": "escalated_repeat",
                        "fingerprint": anomaly.fingerprint,
                        "escalation": escalation_result
                    }
        
        # Normal routing for new or regular alerts
        routing_result = await super().route_anomaly(anomaly)
        
        # Register with the alert tracker
        fingerprint = self.alert_tracker.register_alert(anomaly, routing_result)
        routing_result["fingerprint"] = fingerprint
        
        return routing_result