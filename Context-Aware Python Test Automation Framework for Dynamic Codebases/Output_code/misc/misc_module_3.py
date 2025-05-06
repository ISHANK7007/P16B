class Constraint(ABC):
    """Base interface for all constraint types"""
    @abstractmethod
    def evaluate(self, mutation, context=None):
        """
        Evaluate a mutation against this constraint
        Returns a ConstraintScore with value between 0-1
        """
        pass

class PersonaConstraint(Constraint):
    """Validates alignment with personality, tone, and style guidelines"""
    pass

class FormattingConstraint(Constraint):
    """Validates structural and syntactic requirements"""
    pass

class BoundaryConstraint(Constraint):
    """Enforces generation boundaries like length, topic scope, etc."""
    pass