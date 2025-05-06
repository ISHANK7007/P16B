class AgentCoordinationManager:
    """
    Manages coordination between multiple agents editing the same session
    with optimized message passing and conflict resolution.
    """
    def __init__(self):
        self.session_agents = {}  # Maps session_id -> set of agent_ids
        self.agent_priorities = {}  # Maps (session_id, agent_id) -> priority
        self.shared_locks = {}  # Lightweight distributed locks
        self.event_broker = EventBroker()  # For pub/sub communication
        
    def register_agent(self, session_id, agent_id, priority=0):
        """Register an agent with a session"""
        if session_id not in self.session_agents:
            self.session_agents[session_id] = set()
            
        self.session_agents[session_id].add(agent_id)
        self.agent_priorities[(session_id, agent_id)] = priority
        
        # Subscribe agent to session events
        self.event_broker.subscribe(
            f"session:{session_id}:events",
            agent_id
        )
        
    async def coordinate_edit(self, session_id, agent_id, edit_request):
        """Coordinate an edit from an agent"""
        # Check agent priority
        agent_priority = self.agent_priorities.get((session_id, agent_id), 0)
        
        # Try to acquire a lock for the affected region
        edit_region = (edit_request.position, 
                      edit_request.position + len(edit_request.content))
                      
        lock_acquired = await self._try_acquire_region_lock(
            session_id, agent_id, edit_region, agent_priority)
            
        if not lock_acquired:
            # Cannot edit this region now
            return {
                "status": "deferred",
                "reason": "region_locked"
            }
            
        # Notify other agents about the edit
        await self.event_broker.publish(
            f"session:{session_id}:events",
            {
                "type": "edit_started",
                "agent_id": agent_id,
                "edit_region": edit_region,
                "priority": agent_priority
            }
        )
        
        try:
            # Apply the edit
            edit_result = await self._apply_edit(
                session_id, agent_id, edit_request)
                
            # Notify about completion
            await self.event_broker.publish(
                f"session:{session_id}:events",
                {
                    "type": "edit_completed",
                    "agent_id": agent_id,
                    "edit_id": edit_result["edit_id"],
                    "edit_region": edit_region
                }
            )
            
            return edit_result
        finally:
            # Release the lock
            await self._release_region_lock(
                session_id, agent_id, edit_region)