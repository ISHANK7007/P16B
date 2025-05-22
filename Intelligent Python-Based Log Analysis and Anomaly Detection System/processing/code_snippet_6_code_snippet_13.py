class RoutingTraceAnalyzer:
    def __init__(self, trace_manager, correction_manager):
        self.trace_manager = trace_manager
        self.correction_manager = correction_manager

    def trace(self, alerts):
        return alerts