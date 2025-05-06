class TokenCoherenceValidator:
    """
    Validates token stream coherence using sliding windows and rule-based checks
    to identify hallucinations, semantic breaks, and structural violations.
    """
    def __init__(self, window_size=50, overlap_size=10):
        self.window_size = window_size
        self.overlap_size = overlap_size
        self.validators = []  # List of validation rules
        self.violation_handlers = {}  # Maps violation types to handlers
        self.alert_levels = {
            "warning": 0.3,   # Threshold for warning alerts
            "critical": 0.7   # Threshold for critical alerts
        }
        self.active_tracking = {}  # Track ongoing structures (quotes, lists, etc.)
        
    def register_validator(self, validator):
        """Register a validation rule to apply to token windows"""
        self.validators.append(validator)
        return len(self.validators) - 1  # Return validator ID
        
    def register_violation_handler(self, violation_type, handler):
        """Register a handler for a specific type of violation"""
        self.violation_handlers[violation_type] = handler
        
    def validate_window(self, tokens, metadata=None):
        """Validate a window of tokens for coherence violations"""
        violations = []
        
        for validator in self.validators:
            if validator.should_apply(tokens, metadata, self.active_tracking):
                result = validator.validate(tokens, metadata, self.active_tracking)
                if not result.is_valid:
                    violations.append(result)
        
        # Process violations
        if violations:
            self._process_violations(violations, tokens, metadata)
            
        return violations
        
    def _process_violations(self, violations, tokens, metadata):
        """Process detected violations"""
        for violation in violations:
            # Update active tracking based on violation
            if violation.tracking_updates:
                self.active_tracking.update(violation.tracking_updates)
                
            # Invoke appropriate handler
            if violation.type in self.violation_handlers:
                self.violation_handlers[violation.type](violation, tokens, metadata)