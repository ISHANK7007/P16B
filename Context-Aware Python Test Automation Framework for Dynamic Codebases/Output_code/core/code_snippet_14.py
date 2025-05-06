class StreamingPromptCursor:
    # ... (init method from earlier)
    
    def apply_edit(self, edit_operation, future_only=False):
        """Apply an edit operation with awareness of current generation state"""
        # Identify affected semantic concepts
        affected_concepts = self._identify_affected_concepts(edit_operation)
        
        # Create new alignment marker if this introduces a concept
        if edit_operation.introduces_concept():
            self.alignment_markers[edit_operation.concept] = self.current_position
            
        # Record a rewind checkpoint before applying
        if not future_only:
            self._create_rewind_checkpoint()
            
        # Apply the edit to prompt state
        self.prompt_state.apply_edit(edit_operation, future_only)
        
        # Update semantic windows
        self._update_semantic_windows(edit_operation, affected_concepts)
        
        # Emit change event
        self.event_bus.emit("prompt_updated", {
            "edit": edit_operation,
            "position": self.current_position,
            "affected_concepts": affected_concepts,
            "future_only": future_only
        })
        
    def advance(self, new_token, token_metadata=None):
        """Advance the cursor as new tokens are generated"""
        self.current_position += 1
        self.token_history.append((new_token, token_metadata))
        
        # Check if token satisfies any pending constraints
        satisfied = self._check_constraint_satisfaction(new_token)
        
        # Update semantic relationships for this token
        self._update_token_semantics(new_token)
        
        # Conditionally create checkpoint for safe rewind
        if self._should_create_checkpoint():
            self._create_rewind_checkpoint()
            
        return {
            "position": self.current_position,
            "satisfied_constraints": satisfied,
            "semantic_context": self._get_current_semantic_context()
        }
        
    def rewind_to(self, target_position):
        """Attempt to rewind to a previous position"""
        if target_position >= self.current_position:
            return False, "Cannot rewind to future position"
            
        # Find appropriate rewind scope
        scope = self._find_applicable_rewind_scope(target_position)
        if not scope:
            return False, "No applicable rewind scope"
            
        # Check if rewind is safe
        can_rewind, checkpoint_or_reason = scope.can_rewind_to(target_position)
        if not can_rewind:
            return False, checkpoint_or_reason
            
        # Apply rewind
        self._apply_rewind(checkpoint_or_reason)
        return True, {
            "new_position": self.current_position,
            "restored_state": self.prompt_state.get_snapshot()
        }