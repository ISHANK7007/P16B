class AgentLLMSyncBridge:
    """Bridges the agent decision-making with LLM generation"""
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
        self.agent_state = {}
        self.llm_state = {}
        self.semantic_tracker = SemanticConceptTracker()
        
    async def handle_agent_decision(self, decision):
        """Process a decision from the agent to modify the prompt"""
        # Convert agent decision to edit operation
        edit_op = self._create_edit_operation(decision)
        
        # Get semantic impact analysis
        impact = self.semantic_tracker.analyze_impact(edit_op, self.llm_state)
        
        if impact.requires_user_confirmation:
            # Request user confirmation for high-impact changes
            confirmed = await self._request_user_confirmation(impact)
            if not confirmed:
                return {"status": "rejected", "reason": "user_declined"}
                
        # Apply the edit via orchestrator
        result = await self.orchestrator.process_edit(edit_op)
        
        # Update agent state with results
        self.agent_state.update({
            "last_edit": edit_op,
            "pending_confirmation": result.get("pending_confirmation", None),
            "active_constraints": self._get_active_constraints()
        })
        
        return result