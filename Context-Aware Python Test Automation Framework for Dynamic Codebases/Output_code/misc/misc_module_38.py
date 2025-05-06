class DebugEnhancedPersonaArbiter(PersonaArbiter):
    """
    PersonaArbiter enhanced with debugging for multi-agent mutations
    """
    def __init__(self, voting_strategy="weighted_matrix", conflict_resolution_strategy="hierarchical", debug_manager=None):
        super().__init__(voting_strategy, conflict_resolution_strategy)
        self.debug_manager = debug_manager or MutationDebugManager()
        
    def evaluate_mutations(self, mutation_proposals, context):
        """
        Evaluate mutation proposals with debugging
        """
        # Track which spans are being modified by which personas
        self._register_span_claims(mutation_proposals)
        
        # Enhanced evaluation with debugging 
        final_mutation, report = super().evaluate_mutations(mutation_proposals, context)
        
        # Post-selection analysis for debugging
        violations, debug_report = self.debug_manager.analyze_mutation(final_mutation, context)
        report["debug"] = debug_report
        
        if violations:
            # Record which personas contributed to violations
            self._record_violation_contributions(violations, mutation_proposals)
            report["violations"] = violations
            
        return final_mutation, report
        
    def _register_span_claims(self, mutation_proposals):
        """Register which personas are claiming to modify which spans"""
        span_claims = {}
        
        for proposal in mutation_proposals:
            for span_id in proposal.affected_spans:
                if span_id not in span_claims:
                    span_claims[span_id] = []
                span_claims[span_id].append({
                    "persona_id": proposal.source_persona,
                    "proposal_id": proposal.id,
                    "timestamp": time.time()
                })
                
        # Store in the debug manager for later reference
        self.debug_manager.backtrace_map.metadata["span_claims"] = span_claims
        
    def _record_violation_contributions(self, violations, proposals):
        """Record which personas contributed to each violation"""
        for violation in violations:
            span_id = violation["span_id"]
            contributing_proposals = []
            
            for proposal in proposals:
                if span_id in proposal.affected_spans or span_id in proposal.created_spans:
                    contributing_proposals.append({
                        "proposal_id": proposal.id,
                        "persona_id": proposal.source_persona,
                        "persona_role": proposal.source_persona_role
                    })
                    
            violation["contributing_proposals"] = contributing_proposals