class ConstraintScore:
    """Result of evaluating a single constraint"""
    def __init__(self, value, reason=""):
        self.value = max(0.0, min(1.0, value))  # Force between 0-1
        self.reason = reason

class FusionResult:
    """Result of combining multiple constraint scores"""
    def __init__(self, value, analysis=None):
        self.value = value
        self.analysis = analysis or {}

class MutationScore:
    """Comprehensive evaluation of a mutation candidate"""
    def __init__(self, total, components=None, analysis=None):
        self.total = total  # Overall score
        self.components = components or {}  # Detailed scores by category
        self.analysis = analysis or {}  # Explanation of scoring decisions
        
    def satisfies_threshold(self, threshold=0.7):
        """Check if score meets or exceeds acceptance threshold"""
        return self.total >= threshold