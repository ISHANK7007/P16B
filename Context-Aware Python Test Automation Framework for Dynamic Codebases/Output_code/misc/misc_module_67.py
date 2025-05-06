class EnhancedMutationEngine:
    """
    Mutation engine with support for constraint overrides
    and dissent management across session hops.
    """
    def __init__(self, constraint_resolver, override_manager=None):
        self.constraint_resolver = constraint_resolver
        self.override_manager = override_manager or ConstraintOverrideManager()
        self.session_manager = SessionManager()
        
    def evaluate_mutation(self, mutation, context=None):
        """
        Evaluate a mutation against constraints
        Handles both standard and override mutations
        """
        # Get or create a session context
        session_context = self.session_manager.get_session_context(context)
        
        # For override mutations, use special handling
        if isinstance(mutation, ConstraintOverrideMutation):
            return self._evaluate_override(mutation, session_context, context)
            
        # For standard mutations, use regular evaluation
        return self.constraint_resolver.evaluate_candidate(mutation, context)
        
    def _evaluate_override(self, override_mutation, session_context, context=None):
        """
        Evaluate a mutation with constraint override
        Returns enhanced result with diff and dissent info
        """
        # First evaluate against standard constraints
        standard_result = self.constraint_resolver.evaluate_candidate(
            override_mutation.standard_mutation,
            context
        )
        
        # If all constraints are satisfied, no need for override
        if standard_result.satisfies_threshold():
            result = standard_result.copy()
            result.metadata["override_status"] = "unnecessary"
            return result
            
        # Process the override request
        decision, enhanced_mutation = self.override_manager.process_override_mutation(
            override_mutation,
            standard_result.components,
            session_context
        )
        
        # Create result based on decision
        if decision.allowed:
            # Override allowed, create a passing result
            result = MutationScore(
                total=0.8,  # Good but not perfect score for overrides
                components=standard_result.components,
                analysis={
                    "override_applied": True,
                    "dissent_score": decision.dissent_score,
                    "override_rationale": override_mutation.override_reason
                }
            )
            result.metadata["override_status"] = "approved"
            result.metadata["rationale_diff"] = enhanced_mutation.rationale_diff.to_dict()
            result.metadata["dissent_reports"] = [r.to_dict() for r in enhanced_mutation.dissent_reports]
            
        else:
            # Override denied, use the original failing result
            result = standard_result.copy()
            result.metadata["override_status"] = "denied"
            result.metadata["override_decision"] = decision.to_dict()
            
        return result