class BatchedEvaluationEngine:
    """Process clustered anomalies in batches for efficiency"""
    
    def __init__(
        self, 
        escalation_engine,
        cache: EscalationDecisionCache,
        debouncer: TriggerDebouncer,
        rule_optimizer: RuleEvaluationOptimizer,
        batch_size: int = 100,
        batch_window_seconds: float = 5.0
    ):
        self.escalation_engine = escalation_engine
        self.cache = cache
        self.debouncer = debouncer
        self.rule_optimizer = rule_optimizer
        self.batch_size = batch_size
        self.batch_window = batch_window_seconds
        
        self.pending_anomalies: List[Tuple[Anomaly, str]] = []  # [(anomaly, fingerprint)]
        self.last_batch_time = time.time()
        
        # Performance metrics
        self.total_received = 0
        self.total_batched = 0
        self.total_batches = 0
        self.batch_times: List[float] = []
        
    def queue_anomaly(self, anomaly: Anomaly, fingerprint: str) -> None:
        """Queue an anomaly for batched evaluation"""
        self.total_received += 1
        self.pending_anomalies.append((anomaly, fingerprint))
        
        # Process batch if full or window elapsed
        current_time = time.time()
        if (len(self.pending_anomalies) >= self.batch_size or
            current_time - self.last_batch_time >= self.batch_window):
            self.process_batch()
    
    def process_batch(self) -> List[Dict]:
        """Process all queued anomalies in a batch"""
        if not self.pending_anomalies:
            return []
            
        batch_start_time = time.time()
        batch_size = len(self.pending_anomalies)
        self.total_batches += 1
        self.total_batched += batch_size
        
        # Group anomalies by service for efficient evaluation
        by_service: Dict[str, List[Tuple[Anomaly, str]]] = {}
        for anomaly, fingerprint in self.pending_anomalies:
            service = anomaly.service_name
            if service not in by_service:
                by_service[service] = []
            by_service[service].append((anomaly, fingerprint))
            
        # Process each service group
        results = []
        for service, anomalies in by_service.items():
            service_results = self._process_service_batch(service, anomalies)
            results.extend(service_results)
            
        # Clear pending anomalies
        self.pending_anomalies = []
        self.last_batch_time = time.time()
        
        # Record batch processing time
        batch_time = time.time() - batch_start_time
        self.batch_times.append(batch_time)
        
        return results
    
    def _process_service_batch(
        self, 
        service: str, 
        anomalies: List[Tuple[Anomaly, str]]
    ) -> List[Dict]:
        """Process a batch of anomalies for a single service"""
        results = []
        
        # Group anomalies by escalation level for efficient rule application
        by_level: Dict[EscalationLevel, List[Tuple[Anomaly, str]]] = {}
        
        for anomaly, fingerprint in anomalies:
            # Check if this is a known alert
            if fingerprint in self.escalation_engine.alert_tracker.alerts:
                alert = self.escalation_engine.alert_tracker.alerts[fingerprint]
                level = alert.get("current_escalation_level", EscalationLevel.INITIAL)
                
                if level not in by_level:
                    by_level[level] = []
                by_level[level].append((anomaly, fingerprint))
            else:
                # New alerts go to initial level
                if EscalationLevel.INITIAL not in by_level:
                    by_level[EscalationLevel.INITIAL] = []
                by_level[EscalationLevel.INITIAL].append((anomaly, fingerprint))
                
        # Process each escalation level group
        for level, level_anomalies in by_level.items():
            # Get applicable rules once for this level
            # We'll assume first anomaly is representative of the group
            # for initial rule filtering
            sample_anomaly = level_anomalies[0][0]
            potential_rules = self.rule_optimizer.get_applicable_rules_optimized(
                sample_anomaly, level
            )
            
            # Now process each anomaly using the filtered rule set
            for anomaly, fingerprint in level_anomalies:
                result = self._process_single_anomaly(
                    anomaly, fingerprint, level, potential_rules
                )
                if result:
                    results.append(result)
                    
        return results
    
    def _process_single_anomaly(
        self, 
        anomaly: Anomaly, 
        fingerprint: str,
        level: EscalationLevel,
        potential_rules: List[EscalationRule]
    ) -> Optional[Dict]:
        """Process a single anomaly with optimized rule evaluation"""
        # Check if we should evaluate this anomaly now or debounce
        if not self.debouncer.should_evaluate(fingerprint):
            return None
            
        # Check for cached decision
        for rule in potential_rules:
            cached_result = self.cache.get(fingerprint, rule.id, level)
            if cached_result:
                return cached_result
                
        # No cache hit, evaluate rule
        # Find first applicable rule
        applicable_rule = None
        for rule in potential_rules:
            if self.rule_optimizer.rule_predicates[rule.id](anomaly, level):
                applicable_rule = rule
                break
                
        if not applicable_rule:
            return None
            
        # Execute escalation
        result = asyncio.run(self.escalation_engine._perform_escalation(
            fingerprint, anomaly, applicable_rule
        ))
        
        # Cache the result
        self.cache.set(
            fingerprint, 
            applicable_rule.id, 
            level, 
            result
        )
        
        # Record that an action was taken
        self.debouncer.record_action_taken(fingerprint)
        
        return result
    
    def get_stats(self) -> Dict:
        """Get statistics about batched processing"""
        return {
            "total_received": self.total_received,
            "total_batched": self.total_batched,
            "total_batches": self.total_batches,
            "average_batch_size": self.total_batched / max(self.total_batches, 1),
            "average_batch_time_ms": (sum(self.batch_times) / max(len(self.batch_times), 1)) * 1000,
            "pending_items": len(self.pending_anomalies),
            "cache_stats": self.cache.get_stats(),
            "debouncer_stats": self.debouncer.get_stats()
        }