class SessionManager:
    """
    Manages session contexts and transitions,
    preserving necessary state across session hops.
    """
    def __init__(self):
        self.active_sessions = {}  # Maps session_id to SessionContext
        self.session_lineage = {}  # Maps session_id to parent session_id
        
    def create_session(self, metadata=None):
        """Create a new session context"""
        session_id = str(uuid.uuid4())
        context = SessionContext()
        context.initialize_session(session_id, metadata)
        
        self.active_sessions[session_id] = context
        return session_id, context
        
    def get_session_context(self, context=None):
        """Get session context from global context or create new"""
        if context and "session_id" in context:
            session_id = context["session_id"]
            if session_id in self.active_sessions:
                return self.active_sessions[session_id]
                
        # Create new session
        session_id, context = self.create_session(context.get("session_metadata") if context else None)
        
        # Update global context if provided
        if context:
            context["session_id"] = session_id
            
        return context
        
    def hop_to_new_session(self, original_session_id, metadata=None):
        """
        Create a new session that hops from an existing one,
        preserving lineage
        """
        if original_session_id not in self.active_sessions:
            return self.create_session(metadata)
            
        # Create new session
        new_session_id = str(uuid.uuid4())
        
        # Get original context and create new with hop
        original_context = self.active_sessions[original_session_id]
        new_context = copy.deepcopy(original_context)
        new_context.hop_to_new_session(new_session_id, metadata)
        
        # Record in active sessions
        self.active_sessions[new_session_id] = new_context
        
        # Record lineage
        self.session_lineage[new_session_id] = original_session_id
        
        return new_session_id, new_context
        
    def get_session_chain(self, session_id):
        """Get the chain of session lineage"""
        if session_id not in self.active_sessions:
            return []
            
        return self.active_sessions[session_id].get_session_chain()