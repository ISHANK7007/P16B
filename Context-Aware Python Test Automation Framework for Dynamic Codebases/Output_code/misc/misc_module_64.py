class RationaleDiffEngine:
    """
    Analyzes the difference in rationale between standard constraint
    enforcement and override decisions, generating detailed diffs.
    """
    def __init__(self, semantic_analyzer=None):
        self.semantic_analyzer = semantic_analyzer
        
    def generate_diff(self, standard_rationale, override_rationale, constraint_results):
        """
        Generate a detailed diff between standard and override rationales
        Returns a RationaleDiff object
        """
        # Create the diff object
        diff = RationaleDiff(standard_rationale, override_rationale)
        
        # Analyze semantic differences
        diff.analyze_delta()
        
        # Add relevant constraint context
        self._add_constraint_context(diff, constraint_results)
        
        return diff
        
    def _add_constraint_context(self, diff, constraint_results):
        """Add context from constraint results to the diff"""
        for constraint_id, result in constraint_results.items():
            if not result.get("passed", False):
                # For failed constraints, add the expected behavior
                diff.add_supporting_evidence(
                    evidence_type="constraint_expectation",
                    content=result.get("expected_behavior", ""),
                    source=constraint_id
                )
                
                # Add the violation details
                diff.add_supporting_evidence(
                    evidence_type="constraint_violation",
                    content=result.get("violation_details", ""),
                    source=constraint_id
                )