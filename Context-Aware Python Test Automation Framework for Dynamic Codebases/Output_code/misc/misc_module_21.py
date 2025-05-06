class EnhancedMutationEngine(MutationEngine):
    """
    Enhanced mutation engine that supports both single-agent and multi-agent modes
    """
    def __init__(self, constraint_resolver, generator, coordination_manager=None):
        super().__init__(constraint_resolver, generator)
        self.coordination_manager = coordination_manager
        self.multi_agent_mode = coordination_manager is not None
        
    def apply_best_mutation(self, prompt, context):
        """
        Find and apply the best mutation using either single or multi-agent approach
        """
        if self.multi_agent_mode:
            return self.coordination_manager.process_prompt(prompt, context)
        else:
            # Fall back to original single-agent implementation
            return super().apply_best_mutation(prompt, context)