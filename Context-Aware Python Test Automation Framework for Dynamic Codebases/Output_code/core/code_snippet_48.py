class TokenTraceGenerator:
    """
    Automatically generates ExpectedTokenTraces from successful generations
    to use as templates for validation.
    """
    def __init__(self, cursor):
        self.cursor = cursor
        
    def generate_trace_from_history(self, start_position, end_position, 
                                   importance_calculator=None):
        """Generate an expected trace from generation history"""
        # Ensure we have a current fingerprint
        if not self.cursor.current_fingerprint:
            self.cursor.generate_fingerprint()
            
        # Create new trace
        trace = ExpectedTokenTrace(
            trace_id=str(uuid.uuid4()),
            prompt_fingerprint=self.cursor.current_fingerprint
        )
        
        # Extract token history
        if end_position is None or end_position > self.cursor.current_position:
            end_position = self.cursor.current_position
            
        token_slice = self.cursor.token_history[start_position:end_position + 1]
        
        # Add each token as an expectation
        for i, token_data in enumerate(token_slice):
            token = token_data[0]  # Assuming token_history stores (token, metadata)
            metadata = token_data[1] or {}
            
            # Calculate importance
            if importance_calculator:
                importance = importance_calculator(token, metadata, i)
            else:
                importance = self._default_importance(token, metadata, i)
                
            # Add to trace
            trace.add_expected_token(token, importance=importance)
            
        # Add validation points at key structural boundaries
        self._add_structural_validation_points(trace, token_slice)
        
        # Store the trace
        self.cursor.trace_cache.store_trace(trace)
        
        return trace
        
    def _default_importance(self, token, metadata, position):
        """Default calculation of token importance"""
        # Special tokens get higher importance
        if token.startswith("<") and token.endswith(">"):
            return 0.9
            
        # Punctuation gets medium importance
        if all(c in string.punctuation for c in token):
            return 0.6
            
        # Default importance
        return 0.3
        
    def _add_structural_validation_points(self, trace, token_slice):
        """Add validation points at key structural boundaries"""
        # Look for paragraph breaks, sentence endings, etc.
        for i, (token, metadata) in enumerate(token_slice):
            # End of paragraphs
            if token.strip() == "" and i > 0:
                checkpoint_id = f"para_{i}"
                trace.add_validation_point(i, checkpoint_id)
                
            # End of sentences
            if token in [".", "!", "?"] and i > 0:
                checkpoint_id = f"sent_{i}"
                trace.add_validation_point(i, checkpoint_id)