class StreamConstraint:
    """Defines a constraint to be enforced during token generation"""
    def __init__(self, constraint_type, pattern, replacement=None, priority=0):
        self.constraint_type = constraint_type  # 'prevent', 'ensure', 'transform'
        self.pattern = pattern  # What to look for
        self.replacement = replacement  # What to replace with if applicable
        self.priority = priority  # Higher means applied earlier
        
    def check(self, token_sequence):
        """Check if this constraint is satisfied in the given sequence"""
        if self.constraint_type == "prevent":
            return not self._pattern_matches(token_sequence)
        elif self.constraint_type == "ensure":
            return self._pattern_matches(token_sequence)
        return True