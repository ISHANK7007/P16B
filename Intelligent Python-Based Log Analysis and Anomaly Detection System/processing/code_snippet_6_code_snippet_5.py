class FrequencyBasedEscalationRule(EscalationRule):
    """Escalation rule that triggers based on alert frequency"""
    
    def __init__(
        self,
        name: str,
        frequency_threshold: int,  # Number of occurrences
        time_window: timedelta,    # Time window to count occurrences in
        **kwargs
    ):
        super().__init__(name, **kwargs)
        self.frequency_threshold = frequency_threshold
        self.time_window = time_window
        
class EscalationPolicyEngine:
    # ... existing methods ...
    
    async def check_frequency_based_escalations(self) -> List[Dict]:
        """Check for alerts that need escalation based on frequency"""
        now = datetime.now()
        escalation_actions = []
        frequency_rules = [r for rules in self.rules_by_level.values() 
                         for r in rules if isinstance(r, FrequencyBasedEscalationRule)]
        
        # Also get service-specific frequency rules
        for service_rules in self.service_specific_rules.values():
            service_freq_rules = [r for r in service_rules 
                                if isinstance(r, FrequencyBasedEscalationRule)]
            frequency_rules.extend(service_freq_rules)
            
        # Check each alert against frequency rules
        for fingerprint, alert in self.alert_tracker.alerts.items():
            if alert["state"] in [AlertState.RESOLVED, AlertState.SUPPRESSED]:
                continue
                
            # Check each rule
            for rule in frequency_rules:
                # Skip if doesn't apply to this alert
                if not self._rule_applies(rule, alert["last_anomaly"], alert["current_escalation_level"]):
                    continue
                    
                # Count occurrences in the time window
                window_start = now - rule.time_window
                if alert["first_seen"] > window_start:
                    # Alert started inside the window
                    if alert["count"] >= rule.frequency_threshold:
                        # Threshold exceeded, escalate
                        escalation = await self._perform_escalation(
                            fingerprint, alert["last_anomaly"], rule
                        )
                        escalation_actions.append(escalation)
                        break  # Only apply one rule per alert
        
        return escalation_actions