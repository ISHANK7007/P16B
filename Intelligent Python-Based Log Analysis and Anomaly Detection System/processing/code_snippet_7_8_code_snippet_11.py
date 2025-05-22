class CompiledEscalationRule:
    def __init__(self, id, name, condition_evaluator, action_executor, exception_evaluator):
        self.id = id
        self.name = name
        self.condition_evaluator = condition_evaluator
        self.action_executor = action_executor
        self.exception_evaluator = exception_evaluator
        self.metrics = RuleMetrics()
    
    def evaluate(self, alert_context):
        """Evaluate if rule should be applied to the given alert"""
        self.metrics.increment_evaluation_count()
        
        # Check exceptions first (short circuit if exception applies)
        if self.exception_evaluator and self.exception_evaluator(alert_context):
            self.metrics.increment_exception_count()
            return False
            
        # Evaluate main condition
        if self.condition_evaluator(alert_context):
            self.metrics.increment_match_count()
            return True
            
        return False
    
    async def execute(self, alert_context):
        """Execute rule actions for the given alert"""
        self.metrics.increment_execution_count()
        start_time = time.monotonic()
        
        try:
            result = await self.action_executor(alert_context)
            execution_time = time.monotonic() - start_time
            self.metrics.record_execution_time(execution_time)
            return result
        except Exception as e:
            self.metrics.increment_error_count()
            raise RuleExecutionError(f"Failed to execute rule {self.name}: {str(e)}")