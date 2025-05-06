class MutationDebugManager:
    """
    Central manager for debugging mutation issues
    """
    def __init__(self):
        self.backtrace_map = MutationBacktraceMap()
        self.detectors = []  # List of constraint violation detectors
        self.active_debugging = False  # Whether detailed debugging is enabled
        self.violation_history = []  # History of all violations
        
    def register_detector(self, detector):
        """Register a constraint violation detector"""
        self.detectors.append(detector)
        
    def analyze_mutation(self, mutation, context):
        """
        Analyze a mutation for constraint violations
        Returns a list of violations and a debug report
        """
        violations = []
        
        for detector in self.detectors:
            detector_violations = detector.analyze(mutation, context)
            violations.extend(detector_violations)
            
        if violations:
            self.violation_history.extend(violations)
            
        return violations, self._generate_debug_report(mutation, violations)
        
    def trace_span(self, span_id):
        """Trace the history of a span for debugging"""
        return self.backtrace_map.trace_span_history(span_id)
        
    def find_violation_source(self, violation_id):
        """Analyze a violation to find its root cause"""
        for violation in self.violation_history:
            if violation["id"] == violation_id:
                return self._analyze_violation_source(violation)
        return None
        
    def _analyze_violation_source(self, violation):
        """Determine the root cause of a violation"""
        # Implementation would trace back through span history and dependencies
        # to identify the earliest mutation that contributed to the violation
        pass
        
    def _generate_debug_report(self, mutation, violations):
        """Generate a detailed debug report for a mutation"""
        report = {
            "mutation_id": mutation.id,
            "timestamp": time.time(),
            "violations": violations,
            "affected_spans": [
                self.backtrace_map.span_registry[span_id].to_dict()
                for span_id in mutation.affected_spans
                if span_id in self.backtrace_map.span_registry
            ],
            "created_spans": [
                self.backtrace_map.span_registry[span_id].to_dict()
                for span_id in mutation.created_spans
                if span_id in self.backtrace_map.span_registry
            ],
            "context_dependencies": {
                span_id: list(dependencies)
                for span_id, dependencies in self.backtrace_map.context_dependencies.items()
                if span_id in mutation.affected_spans or span_id in mutation.created_spans
            }
        }
        
        if self.active_debugging:
            # Add additional diagnostic information for active debugging
            report["detailed_span_history"] = {
                span_id: self.trace_span(span_id)
                for span_id in mutation.affected_spans
            }
            
        return report