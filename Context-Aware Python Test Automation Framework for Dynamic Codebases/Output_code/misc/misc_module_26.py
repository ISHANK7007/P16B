class ImplicitConstraintDetector:
    """
    Base class for detectors that identify violations of implicit constraints
    """
    def __init__(self, backtrace_map):
        self.backtrace_map = backtrace_map
        
    @abstractmethod
    def analyze(self, mutation, context):
        """
        Analyze a mutation for constraint violations
        Returns a list of violation records
        """
        pass