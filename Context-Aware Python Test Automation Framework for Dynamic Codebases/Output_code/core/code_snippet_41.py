class MultiAgentSharingOptimizer:
    """
    Optimizes data sharing between agents to reduce duplication
    and minimize communication overhead.
    """
    def __init__(self):
        self.shared_states = {}  # Session-level shared states
        self.agent_views = {}    # Agent-specific views
        self.tombstones = {}     # Track deleted/obsolete data
        
    def create_agent_view(self, session_id, agent_id, view_config=None):
        """Create an optimized view for an agent"""
        if (session_id, agent_id) in self.agent_views:
            return self.agent_views[(session_id, agent_id)]
            
        # Get or create shared session state
        if session_id not in self.shared_states:
            self.shared_states[session_id] = SharedSessionState()
            
        # Create agent view
        view = AgentView(
            session_id=session_id,
            agent_id=agent_id,
            shared_state=self.shared_states[session_id],
            config=view_config
        )
        
        self.agent_views[(session_id, agent_id)] = view
        return view
        
    def share_data(self, session_id, data, scope="session"):
        """Share data among agents with appropriate scope"""
        if session_id not in self.shared_states:
            return False
            
        shared_state = self.shared_states[session_id]
        
        if scope == "session":
            # Share with all agents in session
            shared_state.update(data)
            return True
            
        elif scope.startswith("agent:"):
            # Share with specific agent
            agent_id = scope.split(":", 1)[1]
            view_key = (session_id, agent_id)
            
            if view_key in self.agent_views:
                self.agent_views[view_key].update(data)
                return True
                
        return False
        
    def optimize_message(self, session_id, from_agent_id, to_agent_id, message):
        """Optimize a message between agents by removing already known data"""
        from_view = self.agent_views.get((session_id, from_agent_id))
        to_view = self.agent_views.get((session_id, to_agent_id))
        
        if not from_view or not to_view:
            return message
            
        # Determine what the recipient already knows
        known_data_keys = to_view.get_known_keys()
        
        # Remove redundant data
        optimized = {}
        for key, value in message.items():
            if key not in known_data_keys:
                optimized[key] = value
                
        # Add a reference to shared state for efficiency
        if len(optimized) < len(message):
            optimized["_shared_keys"] = [
                k for k in message if k not in optimized and k != "_shared_keys"
            ]
            
        return optimized