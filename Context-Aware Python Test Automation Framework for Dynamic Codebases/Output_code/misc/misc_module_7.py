class LengthBoundary(BoundaryConstraint):
    """Ensures mutation doesn't cause output to exceed length limits"""
    def __init__(self, max_tokens, min_tokens=0):
        self.max_tokens = max_tokens
        self.min_tokens = min_tokens
        
    def evaluate(self, mutation, context=None):
        # Calculate projected length after mutation
        estimated_tokens = self._estimate_tokens(mutation, context)
        
        if estimated_tokens > self.max_tokens:
            return ConstraintScore(
                value=max(0, 1 - (estimated_tokens - self.max_tokens) / self.max_tokens),
                reason=f"Mutation would exceed max token limit of {self.max_tokens}"
            )
        elif estimated_tokens < self.min_tokens:
            return ConstraintScore(
                value=max(0, estimated_tokens / self.min_tokens),
                reason=f"Mutation would fall below min token limit of {self.min_tokens}"
            )
        return ConstraintScore(value=1.0, reason="Within acceptable length bounds")