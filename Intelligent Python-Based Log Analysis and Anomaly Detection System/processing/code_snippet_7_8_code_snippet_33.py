class AuditableRuleEngine(DSLEnabledAlertRouter):
    """Rule engine that records all evaluations to the ledger"""
    
    def __init__(self, config, escalation_ledger):
        super().__init__(config)
        self.ledger = escalation_ledger
        
    async def _evaluate_rules(self, alert_context):
        """Evaluate rules with auditing"""
        start_time = time.monotonic()
        
        # Find matching rules
        matching_rules = []
        evaluation_results = {}
        
        for rule in self.rule_engine.get_rules():
            # Evaluate rule
            is_match = await rule.evaluate(alert_context)
            evaluation_results[rule.id] = {
                "matched": is_match,
                "evaluation_time_ms": int((time.monotonic() - start_time) * 1000)
            }
            
            if is_match:
                matching_rules.append(rule)
                
        # Record evaluation to ledger
        await self.ledger.record_event(
            alert_id=alert_context.alert.id,
            event_type=EventType.RULE_EVALUATION,
            data={
                "evaluated_rules": len(evaluation_results),
                "matched_rules": len(matching_rules),
                "rule_results": evaluation_results,
                "evaluation_context_hash": self._hash_evaluation_context(alert_context)
            },
            metadata={
                "correlation_id": alert_context.correlation_id,
                "evaluation_timestamp": datetime.utcnow().isoformat()
            }
        )
        
        return matching_rules