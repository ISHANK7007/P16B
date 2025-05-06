class LiveEditSessionManager:
    """
    Manages real-time prompt refinement during streaming completions with sub-token 
    feedback injection capabilities.
    """
    def __init__(self):
        self.active_sessions = {}  # Maps session_id to EditSession objects
        self.event_bus = EventBus()  # For handling edit events asynchronously
        
    def create_session(self, prompt_template, initial_constraints=None):
        """Create a new editing session with initial prompt and constraints"""
        session = EditSession(
            prompt_template=prompt_template,
            constraints=initial_constraints or []
        )
        self.active_sessions[session.id] = session
        return session.id
        
    def apply_edit(self, session_id, edit_operation):
        """Apply an edit operation to an ongoing streaming session"""
        if session_id not in self.active_sessions:
            raise ValueError(f"Session {session_id} not found")
            
        session = self.active_sessions[session_id]
        # Create an overlay patch without interrupting the stream
        patch = EditPatch(edit_operation)
        session.add_patch(patch)
        
        # Emit event for real-time application
        self.event_bus.emit("edit_applied", {
            "session_id": session_id,
            "patch": patch
        })
        
        return patch.id