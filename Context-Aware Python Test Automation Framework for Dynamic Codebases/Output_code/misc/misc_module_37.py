class DebugEnhancedMutationEngine(EnhancedMutationEngine):
    """
    Mutation engine enhanced with debugging capabilities
    """
    def __init__(self, constraint_resolver, generator, coordination_manager=None, debug_manager=None):
        super().__init__(constraint_resolver, generator, coordination_manager)
        self.debug_manager = debug_manager or MutationDebugManager()
        self.repair_suggester = ViolationRepairSuggester(self.debug_manager)
        
    def apply_best_mutation(self, prompt, context):
        """
        Apply best mutation with detailed debugging
        """
        result, report = super().apply_best_mutation(prompt, context)
        
        # Adjust context to include debugging information
        debug_context = context.copy() if context else {}
        debug_context["debug_report"] = report
        
        # Run detailed constraint analysis
        mutations = report.get("applied_mutations", [])
        for mutation in mutations:
            violations, debug_report = self.debug_manager.analyze_mutation(mutation, debug_context)
            
            if violations:
                # Generate repair suggestions
                repair_suggestions = self.repair_suggester.suggest_repairs(violations)
                debug_report["repair_suggestions"] = repair_suggestions
                
                # Store in the result
                if "debug" not in result.metadata:
                    result.metadata["debug"] = []
                result.metadata["debug"].append(debug_report)
                
        return result, report