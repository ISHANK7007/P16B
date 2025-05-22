class DSLEnabledAlertRouter(EnhancedAlertRouter):
    def __init__(self, config):
        super().__init__(config)
        self.rule_engine = EscalationRuleEngine()
        self.parser = EscalationRuleDSLParser()
        self.compiler = EscalationRuleCompiler()
        
        # Load rules from configuration
        for rule_text in config.escalation_rules:
            self._load_rule(rule_text)
    
    def _load_rule(self, rule_text):
        """Parse, validate, compile and register a rule"""
        try:
            ast = self.parser.parse(rule_text)
            validation_result = self.parser.validate(ast)
            compiled_rule = self.compiler.compile(ast)
            self.rule_engine.register_rule(compiled_rule)
            return compiled_rule.id
        except (DSLParsingError, DSLValidationError, DSLCompilationError) as e:
            log.error(f"Failed to load escalation rule: {str(e)}")
            raise
    
    async def _process_alert_batch(self, alerts):
        results = []
        for alert in alerts:
            envelope = self._get_or_create_envelope(alert)
            
            # Create evaluation context with all necessary data
            context = AlertRuleContext(
                alert=alert,
                envelope=envelope,
                fingerprint_data=await self._get_fingerprint_data(alert.anomaly.fingerprint),
                environment_context=self._get_environment_context()
            )
            
            # Find and execute matching rules
            matching_rules = self.rule_engine.find_matching_rules(context)
            for rule in matching_rules:
                await rule.execute(context)
                
            # Update envelope with rule execution results
            envelope.add_extension("applied_rules", [r.id for r in matching_rules])
            
            results.append(envelope)
        
        return results