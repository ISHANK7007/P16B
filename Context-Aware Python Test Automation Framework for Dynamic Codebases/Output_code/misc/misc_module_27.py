class ReferentDropDetector(ImplicitConstraintDetector):
    """
    Detects when a mutation removes a referent that is referenced elsewhere
    """
    def __init__(self, backtrace_map, nlp_engine):
        super().__init__(backtrace_map)
        self.nlp_engine = nlp_engine
        
    def analyze(self, mutation, context):
        """Check if mutation drops referents needed by other spans"""
        violations = []
        
        # Get span IDs affected by this mutation
        affected_spans = self._get_affected_spans(mutation)
        
        for span_id in affected_spans:
            # Find spans that depend on this one
            dependent_spans = self.backtrace_map.get_dependent_spans(span_id)
            
            if not dependent_spans:
                continue
                
            # Extract referents from the original span
            original_referents = self._extract_referents(
                self.backtrace_map.span_registry[span_id].text
            )
            
            # Extract referents from the new/modified span
            new_span_id = self._find_new_span_id(span_id, mutation)
            if not new_span_id:
                # Span was completely removed
                for dependent_id in dependent_spans:
                    violations.append(
                        self.backtrace_map.record_violation(
                            span_id=span_id,
                            violation_type="referent_dropped",
                            description=f"Span containing referents was removed but is still referenced by {dependent_id}",
                            severity="high"
                        )
                    )
                continue
                
            new_referents = self._extract_referents(
                self.backtrace_map.span_registry[new_span_id].text
            )
            
            # Find dropped referents
            dropped_referents = original_referents - new_referents
            
            # Check if any dependents need these referents
            for dependent_id in dependent_spans:
                dependent_span = self.backtrace_map.span_registry.get(dependent_id)
                if not dependent_span:
                    continue
                    
                # Check if dependent uses any dropped referents
                for referent in dropped_referents:
                    if self._uses_referent(dependent_span.text, referent):
                        violations.append(
                            self.backtrace_map.record_violation(
                                span_id=span_id,
                                violation_type="referent_dropped",
                                description=f"Referent '{referent}' was removed but is still used in span {dependent_id}",
                                severity="high"
                            )
                        )
                        
        return violations
        
    def _extract_referents(self, text):
        """Extract potential referents from text using NLP"""
        # This would use a more sophisticated NLP analysis in practice
        # For now, a simplistic implementation:
        return set(re.findall(r'\b[A-Z][a-zA-Z_0-9]*\b', text))  # Extract capitalized words as potential referents
        
    def _uses_referent(self, text, referent):
        """Check if text uses a specific referent"""
        # Simple implementation - would use NLP for coreference resolution
        return referent in text
        
    def _get_affected_spans(self, mutation):
        """Get span IDs affected by this mutation"""
        # Implementation would identify spans affected by the mutation
        pass
        
    def _find_new_span_id(self, original_span_id, mutation):
        """Find the new span ID that replaces the original after mutation"""
        # Implementation would trace mutation to find replacement span
        pass