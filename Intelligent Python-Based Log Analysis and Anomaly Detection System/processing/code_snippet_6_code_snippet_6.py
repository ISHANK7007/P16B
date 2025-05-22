class SuppressionEngine:
    """Manages alert suppression rules and states"""
    
    def __init__(self, alert_tracker: AlertTracker):
        self.alert_tracker = alert_tracker
        self.suppression_rules: Dict[str, Dict] = {}  # pattern -> rule
        
    def add_suppression_rule(self, 
                           pattern: str,  # Can be service, fingerprint pattern, etc.
                           duration: timedelta,
                           reason: str = None,
                           stakeholder_id: str = None) -> str:
        """Add a rule to suppress alerts matching a pattern"""
        rule_id = str(uuid.uuid4())
        self.suppression_rules[rule_id] = {
            "id": rule_id,
            "pattern": pattern,
            "duration": duration,
            "created_at": datetime.now(),
            "expires_at": datetime.now() + duration,
            "created_by": stakeholder_id,
            "reason": reason
        }
        return rule_id
        
    def check_suppression(self, anomaly: Anomaly) -> Tuple[bool, Optional[str]]:
        """Check if an anomaly should be suppressed by any rule"""
        now = datetime.now()
        
        # First check if this specific fingerprint is suppressed
        if self.alert_tracker.is_suppressed(anomaly.fingerprint):
            return True, "fingerprint_suppressed"
            
        # Check rule-based suppression
        for rule_id, rule in self.suppression_rules.items():
            # Skip expired rules
            if now > rule["expires_at"]:
                continue
                
            pattern = rule["pattern"]
            
            # Different pattern matching strategies
            if anomaly.service_name == pattern:
                # Suppress by service
                return True, rule_id
                
            # Could add more matching strategies here:
            # - regex matching on fingerprint
            # - matching on anomaly type
            # - matching combinations of fields
            
        return False, None