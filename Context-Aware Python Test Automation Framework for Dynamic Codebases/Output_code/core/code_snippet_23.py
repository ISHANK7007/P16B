class SlidingWindowValidator:
    """
    Applies TokenCoherenceValidator to sliding windows over the token stream
    to detect coherence issues in near-real-time.
    """
    def __init__(self, validator, window_size=50, stride=10):
        self.validator = validator
        self.window_size = window_size
        self.stride = stride
        self.token_buffer = []
        self.metadata_buffer = []
        self.violation_history = []
        
    def process_token(self, token, metadata=None):
        """Process a new token and run validation if needed"""
        self.token_buffer.append(token)
        self.metadata_buffer.append(metadata or {})
        
        violations = []
        if len(self.token_buffer) >= self.window_size:
            # Validate the current window
            window_tokens = self.token_buffer[-self.window_size:]
            window_metadata = self.metadata_buffer[-self.window_size:]
            
            violations = self.validator.validate_window(window_tokens, window_metadata)
            
            # Slide the window if needed
            if len(self.token_buffer) >= self.window_size + self.stride:
                self.token_buffer = self.token_buffer[-self.window_size:]
                self.metadata_buffer = self.metadata_buffer[-self.window_size:]
                
            # Record violations for history
            if violations:
                self.violation_history.extend(violations)
                
        return violations