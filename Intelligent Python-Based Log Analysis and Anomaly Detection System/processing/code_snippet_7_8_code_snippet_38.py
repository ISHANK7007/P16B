class RoutingTestSandbox:
    """Isolated environment for testing alert routing and escalation policies"""
    
    def __init__(self, config):
        # Setup isolated components with test doubles
        self.rule_engine = TestableRuleEngine(config.rules)
        self.ledger = InMemoryEscalationLedger()
        self.router = TestableAlertRouter(self.rule_engine, self.ledger)
        self.team_registry = TestTeamRegistry(config.teams)
        self.anomaly_generator = SyntheticAnomalyGenerator()
        self.trace_collector = RoutingTraceCollector()
        self.metrics_collector = CoverageMetricsCollector()
        
        # Simulation parameters
        self.time_controller = SimulatedTimeController()
        self.network_simulator = NetworkConditionSimulator()
        
    async def setup_test_scenario(self, scenario):
        """Configure the sandbox for a specific test scenario"""
        # Reset sandbox state
        await self.reset()
        
        # Configure time simulation
        self.time_controller.set_time(scenario.start_time)
        
        # Load test teams
        for team in scenario.teams:
            self.team_registry.register_team(team)
        
        # Load test rules
        for rule in scenario.rules:
            await self.rule_engine.load_rule(rule)
            
        # Register coverage targets
        self.metrics_collector.register_scenario(scenario)
        
        # Configure trace collection
        self.trace_collector.start_collection(
            scenario.name,
            trace_options=scenario.trace_options
        )
    
    async def inject_anomaly(self, anomaly_template, context=None):
        """Inject a synthetic anomaly into the sandbox"""
        # Generate synthetic anomaly
        anomaly = await self.anomaly_generator.generate(
            template=anomaly_template,
            context=context
        )
        
        # Start trace for this anomaly
        trace_id = self.trace_collector.start_trace(anomaly.id)
        
        # Begin routing process
        alert = await self.router.process_anomaly(
            anomaly, 
            trace_id=trace_id
        )
        
        # Collect rule coverage data
        self.metrics_collector.record_evaluation(
            rule_evaluations=self.rule_engine.get_evaluations(),
            matched_rules=self.rule_engine.get_matched_rules()
        )
        
        # Return alert and trace ID for further operations
        return {
            "alert": alert,
            "trace_id": trace_id,
            "anomaly": anomaly
        }
    
    async def simulate_escalation(self, alert_id, time_advance=None):
        """Simulate time advancement to trigger escalation policies"""
        if time_advance:
            advance_amount = time_advance
        else:
            # Default advance enough to trigger next escalation level
            policy = self.rule_engine.get_active_policy(alert_id)
            advance_amount = policy.get_next_escalation_interval() + timedelta(seconds=1)
            
        # Advance simulated time
        self.time_controller.advance(advance_amount)
        
        # Trigger policy evaluation
        result = await self.router.evaluate_escalation(alert_id)
        
        # Record escalation in trace
        self.trace_collector.record_escalation(alert_id, result)
        
        return result
    
    async def simulate_team_action(self, alert_id, team_id, action, metadata=None):
        """Simulate a team taking action on an alert"""
        # Record action in trace
        self.trace_collector.record_team_action(alert_id, team_id, action)
        
        # Process action
        result = await self.router.process_team_action(
            alert_id=alert_id,
            team_id=team_id,
            action=action,
            metadata=metadata
        )
        
        # Record coverage
        self.metrics_collector.record_team_action(team_id, action)
        
        return result
    
    async def get_routing_coverage(self):
        """Get comprehensive routing coverage metrics"""
        return {
            "rule_coverage": self.metrics_collector.get_rule_coverage(),
            "team_coverage": self.metrics_collector.get_team_coverage(),
            "escalation_path_coverage": self.metrics_collector.get_path_coverage(),
            "condition_coverage": self.metrics_collector.get_condition_coverage()
        }
        
    async def get_routing_trace(self, trace_id):
        """Get complete routing trace for analysis"""
        return await self.trace_collector.get_trace(trace_id)
    
    async def validate_against_expected(self, trace_id, expected_outputs):
        """Validate trace against expected routing outputs"""
        trace = await self.trace_collector.get_trace(trace_id)
        validator = RouteTraceValidator()
        
        return await validator.validate(trace, expected_outputs)