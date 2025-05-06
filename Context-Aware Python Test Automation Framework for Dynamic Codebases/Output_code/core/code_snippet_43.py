class ExpectedTokenTrace:
    """
    Represents an expected sequence of tokens that should result
    from a particular prompt path.
    """
    def __init__(self, trace_id, prompt_fingerprint, confidence=1.0):
        self.id = trace_id
        self.prompt_fingerprint = prompt_fingerprint
        self.token_expectations = []  # Sequence of expected tokens/patterns
        self.confidence = confidence  # How confident we are in this trace
        self.validation_points = []   # Key points where validation must occur
        
    def add_expected_token(self, token_pattern, position=None, importance=0.5):
        """Add an expected token or pattern to the trace"""
        if position is None:
            position = len(self.token_expectations)
            
        self.token_expectations.insert(position, {
            "pattern": token_pattern,
            "importance": importance,
            "validated": False
        })
        
        return position
        
    def add_validation_point(self, position, checkpoint_id=None):
        """Add a validation point where token sequence must be checked"""
        validation_point = {
            "position": position,
            "checkpoint_id": checkpoint_id,
            "required_confidence": 0.8,
            "verified": False
        }
        
        self.validation_points.append(validation_point)
        return len(self.validation_points) - 1
        
    def validate_token(self, token, position):
        """Validate a token against the expected trace"""
        if position >= len(self.token_expectations):
            return {"valid": False, "reason": "position_out_of_bounds"}
            
        expectation = self.token_expectations[position]
        pattern = expectation["pattern"]
        
        # Check if token matches pattern
        if isinstance(pattern, str):
            valid = token == pattern
        elif callable(pattern):
            valid = pattern(token)
        elif isinstance(pattern, re.Pattern):
            valid = bool(pattern.match(token))
        else:
            valid = False
            
        # Update validation status
        expectation["validated"] = valid
        
        # Check if we're at a validation point
        validation_results = self._check_validation_points(position)
        
        return {
            "valid": valid,
            "importance": expectation["importance"],
            "validation_points": validation_results
        }
        
    def _check_validation_points(self, current_position):
        """Check if any validation points are triggered by this position"""
        results = []
        
        for i, point in enumerate(self.validation_points):
            if point["position"] == current_position and not point["verified"]:
                # Calculate confidence up to this point
                confidence = self._calculate_confidence(0, current_position)
                
                # Mark as verified if confidence meets requirement
                is_verified = confidence >= point["required_confidence"]
                point["verified"] = is_verified
                
                results.append({
                    "validation_point_id": i,
                    "verified": is_verified,
                    "confidence": confidence,
                    "required_confidence": point["required_confidence"],
                    "checkpoint_id": point["checkpoint_id"]
                })
                
        return results
        
    def _calculate_confidence(self, start_pos, end_pos):
        """Calculate overall confidence in the trace between positions"""
        if start_pos >= end_pos or start_pos >= len(self.token_expectations):
            return 0.0
            
        valid_importance_sum = 0
        total_importance_sum = 0
        
        for i in range(start_pos, min(end_pos + 1, len(self.token_expectations))):
            expectation = self.token_expectations[i]
            importance = expectation["importance"]
            
            total_importance_sum += importance
            
            if expectation["validated"]:
                valid_importance_sum += importance
                
        if total_importance_sum == 0:
            return 0.0
            
        return valid_importance_sum / total_importance_sum