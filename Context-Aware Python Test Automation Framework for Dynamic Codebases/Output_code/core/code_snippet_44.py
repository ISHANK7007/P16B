class TokenTraceCache:
    """
    Caches ExpectedTokenTraces for efficient lookup and validation
    during live editing.
    """
    def __init__(self, max_traces=1000):
        self.traces = {}  # Maps trace_id -> ExpectedTokenTrace
        self.prompt_to_traces = {}  # Maps prompt_fingerprint -> [trace_ids]
        self.checkpoint_to_traces = {}  # Maps checkpoint_id -> [trace_ids]
        self.max_traces = max_traces
        self.stats = {
            "cache_hits": 0,
            "cache_misses": 0,
            "validations_performed": 0
        }
        
    def store_trace(self, trace):
        """Store a token trace in the cache"""
        # Check if we need to evict
        if len(self.traces) >= self.max_traces:
            self._evict_least_used()
            
        # Store the trace
        self.traces[trace.id] = trace
        
        # Update indices
        fingerprint = trace.prompt_fingerprint["fingerprint"]
        if fingerprint not in self.prompt_to_traces:
            self.prompt_to_traces[fingerprint] = []
        self.prompt_to_traces[fingerprint].append(trace.id)
        
        # Index by validation checkpoint
        for point in trace.validation_points:
            if point["checkpoint_id"]:
                checkpoint_id = point["checkpoint_id"]
                if checkpoint_id not in self.checkpoint_to_traces:
                    self.checkpoint_to_traces[checkpoint_id] = []
                self.checkpoint_to_traces[checkpoint_id].append(trace.id)
                
        return trace.id
        
    def get_traces_for_prompt(self, prompt_fingerprint):
        """Get all traces that match a prompt fingerprint"""
        fingerprint_key = prompt_fingerprint["fingerprint"]
        
        if fingerprint_key not in self.prompt_to_traces:
            self.stats["cache_misses"] += 1
            return []
            
        trace_ids = self.prompt_to_traces[fingerprint_key]
        traces = [self.traces[trace_id] for trace_id in trace_ids 
                 if trace_id in self.traces]
                 
        self.stats["cache_hits"] += 1
        return traces
        
    def get_traces_for_checkpoint(self, checkpoint_id):
        """Get all traces that include a specific checkpoint"""
        if checkpoint_id not in self.checkpoint_to_traces:
            return []
            
        trace_ids = self.checkpoint_to_traces[checkpoint_id]
        return [self.traces[trace_id] for trace_id in trace_ids 
               if trace_id in self.traces]
               
    def validate_token_sequence(self, tokens, prompt_fingerprint):
        """Validate a sequence of tokens against expected traces"""
        traces = self.get_traces_for_prompt(prompt_fingerprint)
        
        if not traces:
            return {"valid": False, "reason": "no_matching_traces"}
            
        validation_results = []
        
        for trace in traces:
            trace_result = {
                "trace_id": trace.id,
                "token_validations": [],
                "overall_confidence": 0.0
            }
            
            # Validate each token
            for i, token in enumerate(tokens):
                if i < len(trace.token_expectations):
                    token_result = trace.validate_token(token, i)
                    trace_result["token_validations"].append(token_result)
                    
            # Calculate overall confidence
            trace_result["overall_confidence"] = trace._calculate_confidence(
                0, min(len(tokens) - 1, len(trace.token_expectations) - 1))
                
            validation_results.append(trace_result)
            
        # Determine overall validity
        best_trace = max(validation_results, 
                        key=lambda r: r["overall_confidence"], 
                        default=None)
                        
        self.stats["validations_performed"] += 1
        
        return {
            "valid": best_trace and best_trace["overall_confidence"] >= 0.7,
            "results": validation_results,
            "best_trace": best_trace
        }