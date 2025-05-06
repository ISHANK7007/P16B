class LiveEditSessionManager:
    # Previous implementation...
    
    def initialize_cursor(self, session_id, initial_prompt):
        """Initialize a cursor for bidirectional sync in an edit session"""
        if session_id not in self.active_sessions:
            raise ValueError(f"Session {session_id} not found")
            
        session = self.active_sessions[session_id]
        cursor = StreamingPromptCursor(initial_prompt)
        session.cursor = cursor
        
        # Connect the cursor events to session events
        cursor.event_bus.subscribe("prompt_updated", 
            lambda data: self._handle_prompt_update(session_id, data))
        
        return cursor
    
    def _handle_prompt_update(self, session_id, update_data):
        """Handle prompt updates from cursor"""
        session = self.active_sessions[session_id]
        # Process the update and notify subscribers
        self.event_bus.emit("session_updated", {
            "session_id": session_id,
            "update_type": "prompt",
            "data": update_data
        })