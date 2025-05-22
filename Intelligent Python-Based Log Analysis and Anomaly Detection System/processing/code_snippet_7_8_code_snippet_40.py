class CoverageMetricsCollector:
    """Collects coverage metrics for routing and escalation policies"""
    
    def __init__(self):
        self.rule_executions = defaultdict(int)
        self.rule_matches = defaultdict(int)
        self.condition_executions = defaultdict(int)
        self.condition_results = defaultdict(lambda: {"true": 0, "false": 0})
        self.team_notifications = defaultdict(int)
        self.escalation_paths = defaultdict(int)
        self.registered_rules = set()
        self.registered_teams = set()
        self.registered_paths = set()
    
    def register_scenario(self, scenario):
        """Register elements that should be covered in this scenario"""
        # Register rules
        for rule in scenario.rules:
            self.registered_rules.add(rule.id)
            
            # Register individual conditions
            for condition in rule.conditions:
                self.condition_executions[f"{rule.id}:{condition.id}"] = 0
            
        # Register teams
        for team in scenario.teams:
            self.registered_teams.add(team.id)
            
        # Register expected paths
        for path in scenario.expected_paths:
            self.registered_paths.add(path)
    
    def record_evaluation(self, rule_evaluations, matched_rules):
        """Record rule evaluation metrics"""
        # Record rule executions
        for rule_id in rule_evaluations:
            self.rule_executions[rule_id] += 1
            
        # Record rule matches
        for rule_id in matched_rules:
            self.rule_matches[rule_id] += 1
            
        # Record condition evaluations
        for cond_id, result in rule_evaluations.get("condition_results", {}).items():
            self.condition_executions[cond_id] += 1
            result_key = "true" if result else "false"
            self.condition_results[cond_id][result_key] += 1
    
    def record_team_action(self, team_id, action):
        """Record team action metrics"""
        self.team_notifications[f"{team_id}:{action}"] += 1
    
    def record_escalation_path(self, path_id):
        """Record escalation path execution"""
        self.escalation_paths[path_id] += 1
    
    def get_rule_coverage(self):
        """Get rule coverage metrics"""
        executed = set(self.rule_executions.keys())
        matched = set(self.rule_matches.keys())
        
        return {
            "total_rules": len(self.registered_rules),
            "executed_rules": len(executed),
            "matched_rules": len(matched),
            "execution_percentage": self._percentage(len(executed), len(self.registered_rules)),
            "match_percentage": self._percentage(len(matched), len(self.registered_rules)),
            "rule_details": {
                rule_id: {
                    "executions": self.rule_executions.get(rule_id, 0),
                    "matches": self.rule_matches.get(rule_id, 0)
                } for rule_id in self.registered_rules
            }
        }
    
    def get_condition_coverage(self):
        """Get condition coverage metrics"""
        conditions = set(self.condition_executions.keys())
        
        # Find conditions that have been evaluated both true and false
        fully_covered = [
            cond_id for cond_id, results in self.condition_results.items()
            if results["true"] > 0 and results["false"] > 0
        ]
        
        return {
            "total_conditions": len(self.condition_executions),
            "executed_conditions": len(conditions),
            "fully_covered_conditions": len(fully_covered),
            "full_coverage_percentage": self._percentage(len(fully_covered), len(self.condition_executions)),
            "condition_details": {
                cond_id: {
                    "executions": execs,
                    "true_results": self.condition_results[cond_id]["true"],
                    "false_results": self.condition_results[cond_id]["false"],
                    "fully_covered": self.condition_results[cond_id]["true"] > 0 and 
                                    self.condition_results[cond_id]["false"] > 0
                } for cond_id, execs in self.condition_executions.items()
            }
        }
    
    def _percentage(self, part, total):
        """Calculate percentage with safety for zero division"""
        return (part / total * 100) if total > 0 else 0