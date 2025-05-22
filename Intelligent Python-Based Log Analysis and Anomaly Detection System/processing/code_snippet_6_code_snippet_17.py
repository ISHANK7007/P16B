class RuleEvaluationOptimizer:
    """Optimize escalation rule evaluation for high-volume scenarios"""
    
    def __init__(self, escalation_engine):
        self.escalation_engine = escalation_engine
        self.rule_hit_stats: Dict[str, int] = {}  # rule_id -> hit count
        self.rule_miss_stats: Dict[str, int] = {}  # rule_id -> miss count
        
        # Cached rule predicates for fast evaluation
        self.rule_predicates: Dict[str, Callable] = {}
        
        # Maintain index of rules by service for fast lookup
        self.service_rule_index: Dict[str, List[str]] = {}  # service -> rule_ids
        
        # Track rule evaluation costs
        self.rule_timing_stats: Dict[str, List[float]] = {}  # rule_id -> evaluation times
        
        # Build initial indexes
        self._build_indexes()
    
    def _build_indexes(self) -> None:
        """Build initial rule indexes"""
        for level, rules in self.escalation_engine.rules_by_level.items():
            for rule in rules:
                # Index by service if applicable
                if rule.service_criticality:
                    for service_criticality in rule.service_criticality:
                        key = f"criticality:{service_criticality.name}"
                        if key not in self.service_rule_index:
                            self.service_rule_index[key] = []
                        self.service_rule_index[key].append(rule.id)
                
                # Index by anomaly type if applicable
                if rule.anomaly_types:
                    for anomaly_type in rule.anomaly_types:
                        key = f"anomaly_type:{anomaly_type.name}"
                        if key not in self.service_rule_index:
                            self.service_rule_index[key] = []
                        self.service_rule_index[key].append(rule.id)
                
                # Build predicate function for fast evaluation
                self.rule_predicates[rule.id] = self._build_predicate(rule)
                
                # Initialize statistics
                self.rule_hit_stats[rule.id] = 0
                self.rule_miss_stats[rule.id] = 0
                self.rule_timing_stats[rule.id] = []
    
    def _build_predicate(self, rule: EscalationRule) -> Callable:
        """Build an optimized predicate function for a rule"""
        # This compiles the rule conditions into a fast-path function
        # that can be evaluated without constructing temporary objects
        
        def predicate(anomaly: Anomaly, current_level: EscalationLevel) -> bool:
            # Check service criticality
            if (rule.service_criticality and 
                anomaly.service_criticality not in rule.service_criticality):
                return False
                
            # Check anomaly type
            if rule.anomaly_types and anomaly.anomaly_type not in rule.anomaly_types:
                return False
                
            # Check minimum severity
            if rule.min_severity:
                risk_scorer = self.escalation_engine.risk_scorer
                risk_score = risk_scorer.calculate_risk_score(anomaly)
                urgency = risk_scorer.get_urgency(risk_score)
                if urgency.value < rule.min_severity.value:
                    return False
                    
            # Add other checks here
                
            return True
            
        return predicate
    
    def get_applicable_rules_optimized(
        self, 
        anomaly: Anomaly, 
        current_level: EscalationLevel
    ) -> List[EscalationRule]:
        """Get applicable rules with optimized evaluation"""
        start_time = time.time()
        applicable_rules = []
        
        # Start with service-specific rules
        service = anomaly.service_name
        if service in self.escalation_engine.service_specific_rules:
            service_rules = self.escalation_engine.service_specific_rules[service]
            
            # Fast-path evaluation of service-specific rules
            for rule in service_rules:
                rule_start = time.time()
                if self.rule_predicates[rule.id](anomaly, current_level):
                    self.rule_hit_stats[rule.id] += 1
                    applicable_rules.append(rule)
                else:
                    self.rule_miss_stats[rule.id] += 1
                
                # Record evaluation time
                self.rule_timing_stats[rule.id].append(time.time() - rule_start)
                
            # If we found service-specific rules, return them
            if applicable_rules:
                return applicable_rules
        
        # If no service-specific rules, use indexed lookup
        candidate_rule_ids = set()
        
        # Add rules by criticality
        key = f"criticality:{anomaly.service_criticality.name}"
        if key in self.service_rule_index:
            candidate_rule_ids.update(self.service_rule_index[key])
            
        # Add rules by anomaly type
        key = f"anomaly_type:{anomaly.anomaly_type.name}"
        if key in self.service_rule_index:
            candidate_rule_ids.update(self.service_rule_index[key])
            
        # If we have indexed candidates, evaluate only those
        if candidate_rule_ids:
            for rule_id in candidate_rule_ids:
                for level, rules in self.escalation_engine.rules_by_level.items():
                    for rule in rules:
                        if rule.id == rule_id:
                            rule_start = time.time()
                            if self.rule_predicates[rule.id](anomaly, current_level):
                                self.rule_hit_stats[rule.id] += 1
                                applicable_rules.append(rule)
                            else:
                                self.rule_miss_stats[rule.id] += 1
                            
                            # Record evaluation time
                            self.rule_timing_stats[rule.id].append(time.time() - rule_start)
        else:
            # Fallback to full evaluation
            for rule in self.escalation_engine.rules_by_level[current_level]:
                rule_start = time.time()
                if self.rule_predicates[rule.id](anomaly, current_level):
                    self.rule_hit_stats[rule.id] += 1
                    applicable_rules.append(rule)
                else:
                    self.rule_miss_stats[rule.id] += 1
                
                # Record evaluation time
                self.rule_timing_stats[rule.id].append(time.time() - rule_start)
                
        # Record total evaluation time
        total_time = time.time() - start_time
                
        return applicable_rules
    
    def get_rule_performance_stats(self) -> Dict:
        """Get performance statistics for rule evaluation"""
        stats = {}
        
        for rule_id in self.rule_hit_stats.keys():
            total = self.rule_hit_stats[rule_id] + self.rule_miss_stats[rule_id]
            if total == 0:
                continue
                
            hit_ratio = self.rule_hit_stats[rule_id] / total
            
            timing_data = self.rule_timing_stats.get(rule_id, [])
            avg_time = sum(timing_data) / len(timing_data) if timing_data else 0
            
            stats[rule_id] = {
                "hit_ratio": hit_ratio,
                "total_evaluations": total,
                "avg_evaluation_time_ms": avg_time * 1000,
                "hits": self.rule_hit_stats[rule_id],
                "misses": self.rule_miss_stats[rule_id]
            }
            
        return stats