class SemanticCoherenceDetector(ImplicitConstraintDetector):
    """
    Detects semantic incoherence between related spans across turns
    """
    def __init__(self, backtrace_map, semantic_model):
        super().__init__(backtrace_map)
        self.semantic_model = semantic_model
        
    def analyze(self, mutation, context):
        """Check if mutation creates semantic inconsistencies"""
        violations = []
        
        # Get spans affected by this mutation
        for span_id in mutation.affected_spans:
            # Find semantically related spans
            related_spans = self._find_semantically_related(span_id)
            
            # Find new version of the span after mutation
            new_span_id = self._find_mutation_result(span_id, mutation)
            if not new_span_id:
                continue
                
            new_span = self.backtrace_map.span_registry.get(new_span_id)
            if not new_span:
                continue
                
            # Check semantic coherence with related spans
            for related_id in related_spans:
                related_span = self.backtrace_map.span_registry.get(related_id)
                if not related_span:
                    continue
                    
                coherence_score = self.semantic_model.compute_coherence(
                    new_span.text, related_span.text
                )
                
                if coherence_score < 0.3:  # Arbitrary threshold
                    violations.append(
                        self.backtrace_map.record_violation(
                            span_id=new_span_id,
                            violation_type="semantic_incoherence",
                            description=f"Semantic inconsistency with related span {related_id} (score: {coherence_score:.2f})",
                            severity="medium"
                        )
                    )
                    
        return violations
        
    def _find_semantically_related(self, span_id):
        """Find spans semantically related to this one"""
        # Implementation would use embedding similarity or explicit relationships
        pass
        
    def _find_mutation_result(self, span_id, mutation):
        """Find the resulting span ID after applying a mutation"""
        for op in mutation.span_operations:
            if op["original_span_id"] == span_id:
                return op["new_span_id"]
        return None