class MutationConstraintResolver:
    """
    Evaluates and scores mutation candidates against multiple constraint types.
    Acts as the orchestration layer for constraint resolution.
    """
    def __init__(self, fusion_graph: RuleFusionGraph = None):
        self.constraint_categories = {
            "persona": [],      # Personality/tone constraints
            "formatting": [],   # Structural/syntactic constraints
            "bounds": [],       # Generation boundary constraints
            "domain": []        # Domain-specific constraints
        }
        self.fusion_graph = fusion_graph or RuleFusionGraph()
        
    def register_constraint(self, constraint, category="domain"):
        """Add a constraint to the appropriate category"""
        if category in self.constraint_categories:
            self.constraint_categories[category].append(constraint)
            
    def evaluate_candidate(self, mutation_candidate, context=None):
        """
        Evaluate a mutation candidate against all constraints
        Returns a MutationScore object with detailed metrics
        """
        scores = {}
        for category, constraints in self.constraint_categories.items():
            category_scores = [
                constraint.evaluate(mutation_candidate, context) 
                for constraint in constraints
            ]
            scores[category] = category_scores
            
        # Use the fusion graph to combine scores with appropriate weighting
        final_score = self.fusion_graph.resolve(scores, context)
        return MutationScore(
            total=final_score.value,
            components=scores,
            analysis=final_score.analysis
        )