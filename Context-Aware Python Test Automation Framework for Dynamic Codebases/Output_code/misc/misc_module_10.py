class MutationEngine:
    """Generates, evaluates, and applies prompt mutations"""
    def __init__(self, constraint_resolver, generator):
        self.constraint_resolver = constraint_resolver
        self.mutation_generator = generator
        self.threshold = 0.7
        
    def generate_candidates(self, prompt, context, n=5):
        """Generate n mutation candidates for a prompt"""
        return self.mutation_generator.generate(prompt, context, n)
        
    def apply_best_mutation(self, prompt, context):
        """Find and apply the highest-scoring valid mutation"""
        candidates = self.generate_candidates(prompt, context)
        
        scored_candidates = [
            (candidate, self.constraint_resolver.evaluate_candidate(candidate, context))
            for candidate in candidates
        ]
        
        # Filter by threshold and sort by score
        valid_candidates = [
            (c, s) for c, s in scored_candidates if s.satisfies_threshold(self.threshold)
        ]
        
        if not valid_candidates:
            return None, None  # No valid mutations found
        
        # Select the best candidate
        best_candidate, best_score = max(valid_candidates, key=lambda x: x[1].total)
        mutated_prompt = prompt.apply_mutation(best_candidate)
        
        return mutated_prompt, best_score