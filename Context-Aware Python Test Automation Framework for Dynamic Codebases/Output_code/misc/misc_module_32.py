class InteractiveDebugConsole:
    """
    Interactive console for debugging mutation issues
    """
    def __init__(self, debug_manager, visualizer):
        self.debug_manager = debug_manager
        self.visualizer = visualizer
        
    def start(self):
        """Start the interactive debugging session"""
        # Implementation would provide a command-line or GUI interface
        # for exploring and debugging mutations
        
    def query_span(self, criteria):
        """Find spans matching specific criteria"""
        # Implementation would allow searching for spans by content,
        # turn, timestamp, etc.
        
    def explain_violation(self, violation_id):
        """Generate a human-readable explanation of a violation"""
        # Implementation would provide a clear explanation of what
        # went wrong and why