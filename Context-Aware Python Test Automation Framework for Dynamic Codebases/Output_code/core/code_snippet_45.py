class FingerprintValidatingCursor(StreamingPromptCursor):
    """
    Extends StreamingPromptCursor with fingerprint validation capabilities
    to ensure edit integrity and enable regression rollback.
    """
    def __init__(self, initial_prompt, semantic_window_size=5):
        super().__init__(initial_prompt, semantic_window_size)
        self.fingerprinter = PromptFingerprint()
        self.trace_cache = TokenTraceCache()
        self.checkpoints = {}
        self.forward_validators = []
        self.current_fingerprint = None
        self.validation_enabled = True
        
    def generate_fingerprint(self):
        """Generate a fingerprint for the current prompt state"""
        current_prompt = self.prompt_state.get_effective_prompt()
        metadata = {
            "session_id": self.session_id,
            "checkpoint_ids": list(self.checkpoints.keys()),
            "token_count": len(self.token_history)
        }
        
        self.current_fingerprint = self.fingerprinter.generate(
            current_prompt, metadata)
            
        return self.current_fingerprint
        
    def register_checkpoint(self, checkpoint_id=None):
        """Register a checkpoint for potential rollback"""
        if checkpoint_id is None:
            checkpoint_id = str(uuid.uuid4())
            
        # Create snapshot of current state
        state_snapshot = self._create_checkpoint_snapshot()
        
        # Link checkpoint to current fingerprint
        if self.current_fingerprint is None:
            self.generate_fingerprint()
            
        # Store checkpoint
        self.checkpoints[checkpoint_id] = {
            "fingerprint": self.current_fingerprint,
            "position": self.current_position,
            "timestamp": time.time(),
            "state": state_snapshot
        }
        
        return checkpoint_id
        
    def register_expected_trace(self, checkpoint_id=None):
        """Register an expected token trace starting from current position"""
        if self.current_fingerprint is None:
            self.generate_fingerprint()
            
        trace_id = str(uuid.uuid4())
        trace = ExpectedTokenTrace(trace_id, self.current_fingerprint)
        
        # If checkpoint provided, add validation point
        if checkpoint_id and checkpoint_id in self.checkpoints:
            trace.add_validation_point(0, checkpoint_id)
            
        # Store trace
        self.trace_cache.store_trace(trace)
        return trace
        
    def add_forward_validator(self, validator):
        """Add a function that validates edits before applying"""
        self.forward_validators.append(validator)
        return len(self.forward_validators) - 1
        
    def apply_edit(self, edit_operation, future_only=False):
        """Override to add fingerprint validation before applying edit"""
        # Skip validation if disabled
        if not self.validation_enabled:
            return super().apply_edit(edit_operation, future_only)
            
        # Generate pre-edit fingerprint if needed
        if self.current_fingerprint is None:
            self.generate_fingerprint()
            
        # Simulate the edit
        simulated_prompt = self._simulate_edit(edit_operation)
        edit_fingerprint = self.fingerprinter.generate(
            simulated_prompt, {"edit_id": edit_operation.id})
            
        # Run forward validators
        validation_results = self._run_forward_validators(
            edit_operation, simulated_prompt, edit_fingerprint)
            
        # If any validator fails, reject the edit
        if not all(result["valid"] for result in validation_results):
            # Find the first failure
            failure = next(r for r in validation_results if not r["valid"])
            
            raise EditValidationError(
                f"Edit validation failed: {failure['reason']}",
                validation_results=validation_results,
                edit_operation=edit_operation
            )
            
        # Apply the edit
        result = super().apply_edit(edit_operation, future_only)
        
        # Update fingerprint after edit
        self.current_fingerprint = edit_fingerprint
        
        # Register automatic checkpoint for significant edits
        if self._is_significant_edit(edit_operation):
            checkpoint_id = self.register_checkpoint()
            result["checkpoint_id"] = checkpoint_id
            
        return result
        
    def rollback_to_checkpoint(self, checkpoint_id):
        """Rollback to a previously registered checkpoint"""
        if checkpoint_id not in self.checkpoints:
            return False, "Checkpoint not found"
            
        checkpoint = self.checkpoints[checkpoint_id]
        
        # Verify current state integrity
        current_prompt = self.prompt_state.get_effective_prompt()
        if not self.fingerprinter.verify(current_prompt, self.current_fingerprint):
            return False, "Current state integrity check failed"
            
        # Restore from checkpoint
        self._restore_from_snapshot(checkpoint["state"])
        self.current_position = checkpoint["position"]
        self.current_fingerprint = checkpoint["fingerprint"]
        
        return True, {
            "restored_position": self.current_position,
            "checkpoint_id": checkpoint_id
        }
        
    def advance(self, new_token, token_metadata=None):
        """Override to validate token against expected traces"""
        # Regular advance functionality
        advance_result = super().advance(new_token, token_metadata)
        
        # Skip validation if disabled
        if not self.validation_enabled:
            return advance_result
            
        # Validate token against expected traces
        if self.current_fingerprint:
            validation = self._validate_token_against_traces(
                new_token, self.current_position - 1)
                
            advance_result["fingerprint_validation"] = validation
            
            # Check if any validation points triggered
            self._process_validation_points(validation)
            
        return advance_result
        
    def _validate_token_against_traces(self, token, position):
        """Validate a token against expected traces"""
        traces = self.trace_cache.get_traces_for_prompt(self.current_fingerprint)
        
        if not traces:
            return {"valid": True, "reason": "no_expectations"}
            
        results = []
        for trace in traces:
            if position < len(trace.token_expectations):
                result = trace.validate_token(token, position)
                results.append({
                    "trace_id": trace.id,
                    "result": result
                })
                
        # If we have results, check if any failed critically
        critical_failures = [r for r in results 
                           if not r["result"]["valid"] 
                           and r["result"]["importance"] > 0.8]
                           
        if critical_failures:
            return {
                "valid": False,
                "reason": "critical_expectation_failure",
                "failures": critical_failures,
                "all_results": results
            }
            
        return {"valid": True, "results": results}
        
    def _run_forward_validators(self, edit, simulated_prompt, fingerprint):
        """Run all forward validators on a proposed edit"""
        results = []
        
        for validator in self.forward_validators:
            try:
                result = validator(edit, simulated_prompt, fingerprint, self)
                results.append(result)
            except Exception as e:
                results.append({
                    "valid": False,
                    "reason": f"validator_error: {str(e)}",
                    "exception": e
                })
                
        return results