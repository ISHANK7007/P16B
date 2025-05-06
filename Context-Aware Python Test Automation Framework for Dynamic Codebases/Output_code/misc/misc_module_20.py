class MutationCoordinationManager:
    """
    Coordinates the multi-agent mutation process from proposal to selection
    """
    def __init__(self, arbiter, mutation_engine):
        self.arbiter = arbiter
        self.mutation_engine = mutation_engine
        self.agents = {}  # Map of agent_id to Agent objects
        
    def register_agent(self, agent, persona):
        """Register an agent with its persona profile"""
        self.agents[agent.id] = agent
        self.arbiter.register_persona(persona)
        
    def process_prompt(self, prompt, context=None):
        """
        Process a prompt through the multi-agent system:
        1. Distribute to appropriate agents
        2. Collect mutation proposals
        3. Arbitrate between conflicting proposals
        4. Apply winning mutations
        """
        # Step 1: Determine which agents should review this prompt
        selected_agents = self._select_relevant_agents(prompt, context)
        
        # Step 2: Distribute prompt to selected agents and collect proposals
        proposals = []
        for agent in selected_agents:
            agent_proposals = agent.generate_mutations(prompt, context)
            for proposal in agent_proposals:
                proposals.append(MutationProposal(
                    mutation=proposal,
                    source_persona=agent.persona_id,
                    source_persona_role=agent.role,
                    metadata={"agent_confidence": agent.get_confidence(proposal)}
                ))
                
        # Step 3: Score proposals using MutationConstraintResolver
        for proposal in proposals:
            quality_score = self.mutation_engine.constraint_resolver.evaluate_candidate(
                proposal.mutation, context).total
            proposal.quality_score = quality_score
                
        # Step 4: Arbitrate between proposals
        final_mutation, report = self.arbiter.evaluate_mutations(proposals, context)
        
        # Step 5: Apply the winning mutation(s)
        if final_mutation:
            result = prompt.apply_mutation(final_mutation)
            return result, report
        return prompt, report  # No changes if no valid mutations
        
    def _select_relevant_agents(self, prompt, context):
        """Select which agents should review this prompt based on expertise and role"""
        selected = []
        
        # Always include safety monitors
        for agent_id, agent in self.agents.items():
            if agent.role == "safety_monitor":
                selected.append(agent)
                
        # Select domain experts based on context
        if context and "domain" in context:
            domain = context["domain"]
            for agent_id, agent in self.agents.items():
                if agent.has_domain_expertise(domain) and agent not in selected:
                    selected.append(agent)
                    
        # Add general-purpose agents to ensure coverage
        for agent_id, agent in self.agents.items():
            if agent.role == "editor" and agent not in selected:
                selected.append(agent)
                
        return selected