class RoutingTestRunner:
    """Test runner for executing routing tests in CI pipeline"""
    
    def __init__(self, config_path):
        self.config_path = config_path
        self.test_scenarios = []
        self.results = []
        self.sandbox = None
    
    async def load_scenarios(self):
        """Load test scenarios from configuration"""
        with open(self.config_path, 'r') as f:
            config = yaml.safe_load(f)
            
        # Load each scenario
        for scenario_config in config.get('scenarios', []):
            scenario = TestScenario(
                name=scenario_config['name'],
                description=scenario_config.get('description', ''),
                rules=self._load_rules(scenario_config.get('rules', [])),
                teams=self._load_teams(scenario_config.get('teams', [])),
                anomalies=scenario_config.get('anomalies', []),
                expected_paths=scenario_config.get('expected_paths', []),
                expected_outputs=scenario_config.get('expected_outputs', {}),
                trace_options=scenario_config.get('trace_options', {})
            )
            self.test_scenarios.append(scenario)
            
        return len(self.test_scenarios)
    
    async def run_tests(self):
        """Run all test scenarios"""
        # Initialize sandbox
        self.sandbox = RoutingTestSandbox(TestConfig())
        
        # Run each scenario
        for scenario in self.test_scenarios:
            result = await self._run_scenario(scenario)
            self.results.append(result)
            
        # Generate overall results
        return self._generate_summary()
    
    async def _run_scenario(self, scenario):
        """Run a single test scenario"""
        # Setup scenario
        await self.sandbox.setup_test_scenario(scenario)
        
        # Track results
        scenario_results = {
            "name": scenario.name,
            "description": scenario.description,
            "anomaly_results": [],
            "validation_results": [],
            "coverage": None,
            "passed": True
        }
        
        # Inject each anomaly
        for anomaly_config in scenario.anomalies:
            # Process anomaly
            anomaly_result = await self._process_anomaly(anomaly_config)
            scenario_results["anomaly_results"].append(anomaly_result)
            
            # Check expectations
            validation = await self.sandbox.validate_against_expected(
                anomaly_result["trace_id"],
                scenario.expected_outputs
            )
            scenario_results["validation_results"].append(validation)
            
            if not validation["passed"]:
                scenario_results["passed"] = False
        
        # Get coverage
        scenario_results["coverage"] = await self.sandbox.get_routing_coverage()
        
        return scenario_results
    
    async def _process_anomaly(self, anomaly_config):
        """Process a single anomaly through the test lifecycle"""
        # Inject anomaly
        result = await self.sandbox.inject_anomaly(
            anomaly_config["template"],
            context=anomaly_config.get("context")
        )
        
        # Process actions
        for action in anomaly_config.get("actions", []):
            if action["type"] == "wait":
                await asyncio.sleep(action["duration"])
            elif action["type"] == "escalate":
                await self.sandbox.simulate_escalation(
                    result["alert"]["id"],
                    time_advance=action.get("time_advance")
                )
            elif action["type"] == "team_action":
                await self.sandbox.simulate_team_action(
                    result["alert"]["id"],
                    action["team_id"],
                    action["action"],
                    metadata=action.get("metadata")
                )
        
        # Complete trace
        self.sandbox.trace_collector.complete_trace(
            result["trace_id"],
            "completed"
        )
        
        return {
            "alert_id": result["alert"]["id"],
            "trace_id": result["trace_id"],
            "anomaly_type": result["anomaly"].type.value
        }
    
    def _generate_summary(self):
        """Generate overall test summary"""
        total_scenarios = len(self.results)
        passed_scenarios = sum(1 for r in self.results if r["passed"])
        
        # Calculate overall coverage
        rule_coverage = self._calculate_overall_coverage(
            [r["coverage"]["rule_coverage"] for r in self.results]
        )
        
        team_coverage = self._calculate_overall_coverage(
            [r["coverage"]["team_coverage"] for r in self.results]
        )
        
        return {
            "total_scenarios": total_scenarios,
            "passed_scenarios": passed_scenarios,
            "pass_percentage": (passed_scenarios / total_scenarios * 100) if total_scenarios > 0 else 0,
            "overall_rule_coverage": rule_coverage,
            "overall_team_coverage": team_coverage,
            "scenario_results": [
                {
                    "name": r["name"],
                    "passed": r["passed"],
                    "rule_coverage": r["coverage"]["rule_coverage"]["execution_percentage"],
                    "failing_validations": len([v for v in r["validation_results"] if not v["passed"]])
                } for r in self.results
            ]
        }