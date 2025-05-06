class ViolationRepairSuggester:
    """
    Suggests fixes for detected constraint violations
    """
    def __init__(self, debug_manager):
        self.debug_manager = debug_manager
        self.repair_strategies = {}  # Maps violation type to repair strategy
        
    def register_repair_strategy(self, violation_type, strategy):
        """Register a repair strategy for a violation type"""
        self.repair_strategies[violation_type] = strategy
        
    def suggest_repairs(self, violations):
        """
        Generate repair suggestions for a list of violations
        Returns a map of violation IDs to suggested repairs
        """
        suggestions = {}
        
        for violation in violations:
            violation_type = violation["violation_type"]
            if violation_type in self.repair_strategies:
                strategy = self.repair_strategies[violation_type]
                suggestions[violation["span_id"]] = strategy.generate_suggestions(violation)
                
        return suggestions