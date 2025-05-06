class ArbitrationMetrics:
    """Metrics for evaluating arbitration decisions against persona divergence"""
    
    @staticmethod
    def calculate_arbitration_quality(
        divergence_analysis: PersonaDivergenceAnalysis,
        arbitration_result: PromptMutation,
        persona_weights: Dict[str, float] = None
    ) -> Dict[str, Any]:
        """Calculate metrics for arbitration quality"""
        decisions = divergence_analysis.decisions
        
        # If no weights provided, use equal weights
        if persona_weights is None:
            persona_weights = {d.persona_id: 1.0 for d in decisions}
            
        # Normalize weights
        weight_sum = sum(persona_weights.values())
        normalized_weights = {
            pid: w / weight_sum for pid, w in persona_weights.items()
        }
        
        # Find which decision corresponds to the arbitration result
        arbitration_hash = hashlib.sha256(arbitration_result.mutated.encode()).hexdigest()
        
        # Map each persona's decision to a similarity score with the arbitration result
        arbitration_similarities = {}
        for decision in decisions:
            # Simple text similarity - could use more sophisticated metrics
            decision_hash = hashlib.sha256(decision.mutated_prompt.encode()).hexdigest()
            
            # Perfect match gets 1.0 similarity
            if decision_hash == arbitration_hash:
                arbitration_similarities[decision.persona_id] = 1.0
            else:
                # Calculate similarity based on text overlap
                # This is a simplified approach - real implementation would use better similarity metrics
                from difflib import SequenceMatcher
                similarity = SequenceMatcher(
                    None, decision.mutated_prompt, arbitration_result.mutated
                ).ratio()
                arbitration_similarities[decision.persona_id] = similarity
        
        # Calculate weighted average similarity (higher is better)
        weighted_similarity = sum(
            normalized_weights.get(pid, 0) * sim 
            for pid, sim in arbitration_similarities.items()
        )
        
        # Calculate metrics
        metrics = {
            "weighted_similarity": weighted_similarity,
            "similarity_by_persona": arbitration_similarities,
            "arbitration_entropy": 0.0,  # Will calculate below
            "decision_support": 0.0      # Will calculate below
        }
        
        # Find which cluster the arbitration belongs to
        arbitration_cluster = -1
        for i, cluster in enumerate(divergence_analysis.decision_clusters):
            # Check if any persona in this cluster produced a result that matches arbitration
            cluster_hashes = [
                hashlib.sha256(d.mutated_prompt.encode()).hexdigest()
                for d in decisions if d.persona_id in cluster
            ]
            if arbitration_hash in cluster_hashes or any(
                SequenceMatcher(None, arbitration_result.mutated, d.mutated_prompt).ratio() > 0.9
                for d in decisions if d.persona_id in cluster
            ):
                arbitration_cluster = i
                break
                
        # Calculate decision support metrics
        if arbitration_cluster >= 0:
            # The arbitration matches a known cluster
            cluster = divergence_analysis.decision_clusters[arbitration_cluster]
            cluster_size = len(cluster)
            cluster_weight = sum(normalized_weights.get(pid, 0) for pid in cluster)
            
            metrics["decision_support"] = cluster_weight
            metrics["supporting_personas"] = cluster
            metrics["support_ratio"] = cluster_size / len(decisions)
            
            # Entropy calculation based on cluster selection
            # Lower entropy means the arbitration was more predictable
            probability = cluster_weight
            metrics["arbitration_entropy"] = -probability * np.log2(probability) if probability > 0 else 0
            
        else:
            # The arbitration doesn't match any known cluster - it's a novel solution
            metrics["decision_support"] = 0.0
            metrics["supporting_personas"] = []
            metrics["support_ratio"] = 0.0
            metrics["arbitration_entropy"] = 1.0  # Maximum entropy/surprise
            metrics["is_novel_solution"] = True
            
        return metrics

class DivergenceAwareArbitrationScorer:
    """Enhanced arbitration scorer that accounts for persona divergence"""
    
    def __init__(self, 
                divergence_service: DivergenceAnalysisService,
                persona_replay_simulator: PersonaReplaySimulator):
        self.divergence_service = divergence_service
        self.simulator = persona_replay_simulator
        self.arbitration_metrics: Dict[str, Dict[str, Any]] = {}
    
    async def score_arbitration_with_divergence(self,
                                             mutation_id: str,
                                             arbitration_result: PromptMutation,
                                             persona_weights: Dict[str, float] = None) -> Dict[str, Any]:
        """Score an arbitration result considering persona divergence"""
        # Get or generate the divergence analysis
        analysis = await self.divergence_service.get_cached_analysis(mutation_id)
        
        if not analysis:
            # We need to simulate with personas first
            trace = self.simulator.replay_engine.trace_repository.get(mutation_id)
            if not trace:
                return {"error": f"Trace {mutation_id} not found"}
            
            # Run the simulation
            simulation_result = await self.simulator.simulate_with_personas(trace)
            if "error" in simulation_result:
                return simulation_result
                
            # Retrieve the analysis
            analysis = await self.divergence_service.get_cached_analysis(mutation_id)
            if not analysis:
                return {"error": "Failed to generate divergence analysis"}
        
        # Calculate arbitration metrics
        metrics = ArbitrationMetrics.calculate_arbitration_quality(
            divergence_analysis=analysis,
            arbitration_result=arbitration_result,
            persona_weights=persona_weights
        )
        
        # Store metrics for later reference
        self.arbitration_metrics[mutation_id] = metrics
        
        # Add relevant divergence analysis for context
        metrics["divergence_entropy"] = analysis.entropy
        metrics["agreement_rate"] = analysis.agreement_rate
        metrics["decision_clusters"] = len(analysis.decision_clusters)
        
        # Calculate an overall arbitration score (0-1 range)
        if metrics.get("is_novel_solution", False):
            # Novel solutions get scored based on weighted similarity
            weight_factor = 0.7  # How much weight to give to similarity vs. novelty
            metrics["arbitration_score"] = weight_factor * metrics["weighted_similarity"] + (1 - weight_factor) * 0.5
            metrics["arbitration_category"] = "Novel Solution"
        else:
            # Known solutions scored by support and similarity
            support_weight = 0.6  # How much weight to give to support vs. similarity
            metrics["arbitration_score"] = (
                support_weight * metrics["decision_support"] + 
                (1 - support_weight) * metrics["weighted_similarity"]
            )
            
            # Categorize the arbitration
            if metrics["support_ratio"] > 0.75:
                metrics["arbitration_category"] = "Consensus Selection"
            elif metrics["support_ratio"] > 0.5:
                metrics["arbitration_category"] = "Majority Selection"
            elif metrics["support_ratio"] > 0.25:
                metrics["arbitration_category"] = "Plurality Selection"
            else:
                metrics["arbitration_category"] = "Minority Selection"
        
        return metrics

    async def evaluate_arbitration_strategy(self,
                                        strategy_name: str,
                                        mutation_ids: List[str],
                                        arbitration_results: Dict[str, PromptMutation],
                                        persona_weights: Dict[str, float] = None) -> Dict[str, Any]:
        """Evaluate an arbitration strategy across multiple mutations"""
        strategy_metrics = {
            "strategy_name": strategy_name,
            "mutation_count": len(mutation_ids),
            "average_score": 0.0,
            "category_distribution": {},
            "divergence_correlation": 0.0,
            "mutation_results": {}
        }
        
        scores = []
        entropy_values = []
        
        for mutation_id in mutation_ids:
            if mutation_id not in arbitration_results:
                strategy_metrics["mutation_results"][mutation_id] = {
                    "error": "No arbitration result available"
                }
                continue
                
            arbitration_result = arbitration_results[mutation_id]
            
            # Score this arbitration
            metrics = await self.score_arbitration_with_divergence(
                mutation_id=mutation_id,
                arbitration_result=arbitration_result,
                persona_weights=persona_weights
            )
            
            if "error" in metrics:
                strategy_metrics["mutation_results"][mutation_id] = metrics
                continue
                
            # Store the individual result
            strategy_metrics["mutation_results"][mutation_id] = metrics
            
            # Update aggregates
            scores.append(metrics["arbitration_score"])
            entropy_values.append(metrics["divergence_entropy"])
            
            # Update category counts
            category = metrics["arbitration_category"]
            strategy_metrics["category_distribution"][category] = (
                strategy_metrics["category_distribution"].get(category, 0) + 1
            )
        
        # Calculate overall metrics
        if scores:
            strategy_metrics["average_score"] = np.mean(scores)
            strategy_metrics["score_std_dev"] = np.std(scores)
            
            # Convert category counts to percentages
            for category, count in strategy_metrics["category_distribution"].items():
                strategy_metrics["category_distribution"][category] = count / len(scores)
            
            # Calculate correlation between divergence and arbitration score
            if len(scores) > 1 and len(entropy_values) == len(scores):
                correlation = np.corrcoef(entropy_values, scores)[0, 1]
                strategy_metrics["divergence_correlation"] = correlation
        
        return strategy_metrics

class EnhancedMutationReplayEngine(MutationReplayEngine):
    """Enhanced replay engine with persona divergence analysis capabilities"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.divergence_service = DivergenceAnalysisService()
        self.persona_simulator = None  # Will initialize later
        self.arbitration_scorer = None  # Will initialize later
        
    def initialize_persona_components(self, personas: Dict[str, Persona]):
        """Initialize persona-related components"""
        self.persona_simulator = PersonaReplaySimulator(
            replay_engine=self,
            personas=personas,
            divergence_service=self.divergence_service
        )
        
        self.arbitration_scorer = DivergenceAwareArbitrationScorer(
            divergence_service=self.divergence_service,
            persona_replay_simulator=self.persona_simulator
        )
    
    async def replay_trace_with_persona(self, 
                                    trace_id: str, 
                                    persona: Persona,
                                    context: ExecutionContext) -> SimulationResult:
        """Replay a trace with a specific persona's influence"""
        # Extend the replay_trace method to account for persona influence
        
        # Get the basic trace
        trace = self.trace_repository.get(trace_id)
        if not trace:
            raise ValueError(f"Trace {trace_id} not found")
        
        # Apply the persona's style to the mutation
        # This would modify how the mutation is evaluated based on persona characteristics
        # For example, an EXPERT persona might apply stricter validation than a CREATIVE persona
        
        # Simplified implementation - in a real system, would use the persona's 
        # characteristics to influence the replay
        constraint_strictness = 1.0  # Default strictness
        
        if persona.type == PersonaType.EXPERT:
            constraint_strictness = 1.2  # Experts are more strict
        elif persona.type == PersonaType.CREATIVE:
            constraint_strictness = 0.8  # Creative personas are more lenient
        
        # Modify context based on persona
        context.parameters["constraint_strictness"] = constraint_strictness
        context.parameters["expertise_areas"] = persona.expertise
        
        # Execute the replay with the modified context
        return await self._execute_replay_with_context(trace, context)
    
    async def _execute_replay_with_context(self, 
                                      trace: MutationTrace, 
                                      context: ExecutionContext) -> SimulationResult:
        """Execute a replay with a specific context"""
        # This would be implemented similarly to the replay_trace method,
        # but with modifications to account for the context parameters
        
        # Simplified implementation for illustration
        # In a real system, this would execute the actual replay logic
        
        # Create a sandbox with the preserved context
        constraints = context.constraint_set or []
        
        # Adjust constraint application based on strictness if specified
        strictness = context.parameters.get("constraint_strictness", 1.0)
        
        # Simplified constraint adjustment
        adjusted_constraints = constraints
        if strictness != 1.0:
            # In a real implementation, would clone and modify constraint thresholds
            # This is just a placeholder
            adjusted_constraints = constraints
        
        # Create a constrained mutation engine
        constraint_manager = ConstraintManager(adjusted_constraints)
        engine = MutationEngine(constraint_manager)
        
        # Execute the mutation with modified parameters
        # This is highly simplified - the real implementation would 
        # be more sophisticated about how it applies persona characteristics
        import random
        original_state = random.getstate()
        random.seed(context.random_seed)
        
        try:
            # Simulate persona-specific mutation
            # In a real implementation, persona would influence the actual mutation algorithm
            
            # For simulation, we'll just slightly modify the mutated prompt
            # based on persona parameters to demonstrate the concept
            persona = context.parameters.get("persona", {})
            persona_type = persona.get("type", "GENERALIST")
            expertise = persona.get("expertise", [])
            mutation_style = persona.get("mutation_style", "balanced")
            
            # Apply a simulated "persona lens" to the prompt
            mutated_prompt = trace.mutated_prompt
            
            # Simulate slight variations in output based on persona
            if persona_type == "EXPERT" and any(area.lower() in trace.mutated_prompt.lower() for area in expertise):
                # Experts add more technical precision in their domain
                mutated_prompt += f"\n\nNote: This approach follows best practices for {', '.join(expertise[:2])}."
            elif persona_type == "CREATIVE":
                # Creative personas might add flourishes
                mutated_prompt += "\n\nThis creative approach offers several novel advantages."
            
            # Create a simulated result
            success = random.random() < 0.8  # 80% success rate
            
            # Simplified validation results
            validation_results = {
                "grammar_valid": random.random() < 0.95,
                "model_compatible": True,
                "constraint_details": {
                    f"constraint_{i}": random.random() < (0.9 * strictness)
                    for i in range(3)
                }
            }
            
            result = SimulationResult(
                mutation_id=trace.mutation_id,
                success=success,
                replay_output=mutated_prompt,
                validation_results=validation_results,
                execution_metrics={"latency": random.uniform(0.5, 2.0)},
                llm_response={
                    "explanation": f"Applied {persona_type.lower()} perspective with focus on {mutation_style}.",
                }
            )
            
            return result
            
        finally:
            # Restore random state
            random.setstate(original_state)
    
    async def compare_arbitration_strategies(self,
                                        mutation_ids: List[str],
                                        strategies: Dict[str, Callable[[List[PromptMutation]], PromptMutation]],
                                        personas: Optional[List[str]] = None) -> Dict[str, Any]:
        """Compare different arbitration strategies using divergence analysis"""
        # Ensure persona components are initialized
        if not self.persona_simulator or not self.arbitration_scorer:
            return {"error": "Persona components not initialized"}
        
        # First, simulate all mutations with personas to generate divergence data
        simulation_results = await self.persona_simulator.batch_simulate_mutations(
            mutation_ids=mutation_ids,
            persona_ids=personas
        )
        
        # For each strategy, generate arbitration results
        strategy_results = {}
        arbitration_by_strategy = {}
        
        for mutation_id in mutation_ids:
            if "error" in simulation_results.get(mutation_id, {}):
                continue
                
            # Get the persona decisions for this mutation
            simulation = simulation_results[mutation_id]
            decision_dicts = simulation.get("decisions", [])
            
            # Convert to PromptMutation objects for arbitration
            mutations = []
            for decision in decision_dicts:
                mutation = PromptMutation(
                    original=decision["original_prompt"],
                    mutated=decision["mutated_prompt"],
                    format=PromptFormat.RAW_TEXT,  # Simplified - would use actual format
                    mutation_rationale=decision["explanation"]
                )
                mutations.append(mutation)
            
            # Apply each strategy
            for strategy_name, strategy_fn in strategies.items():
                if strategy_name not in arbitration_by_strategy:
                    arbitration_by_strategy[strategy_name] = {}
                    
                try:
                    arbitration_result = strategy_fn(mutations)
                    arbitration_by_strategy[strategy_name][mutation_id] = arbitration_result
                    
                except Exception as e:
                    print(f"Strategy {strategy_name} failed on mutation {mutation_id}: {e}")
        
        # Evaluate each strategy
        for strategy_name, arbitration_results in arbitration_by_strategy.items():
            evaluation = await self.arbitration_scorer.evaluate_arbitration_strategy(
                strategy_name=strategy_name,
                mutation_ids=mutation_ids,
                arbitration_results=arbitration_results
            )
            
            strategy_results[strategy_name] = evaluation
        
        # Compile comparison report
        if strategy_results:
            strategies_sorted = sorted(
                strategy_results.items(),
                key=lambda x: x[1]["average_score"],
                reverse=True
            )
            
            # Overall ranking
            ranking = [{"strategy": name, "score": metrics["average_score"]} 
                     for name, metrics in strategies_sorted]
            
            # Find best strategy per mutation
            best_by_mutation = {}
            for mutation_id in mutation_ids:
                best_strategy = None
                best_score = -1
                
                for strategy_name, evaluation in strategy_results.items():
                    if mutation_id in evaluation["mutation_results"]:
                        result = evaluation["mutation_results"][mutation_id]
                        if "arbitration_score" in result and result["arbitration_score"] > best_score:
                            best_score = result["arbitration_score"]
                            best_strategy = strategy_name
                
                if best_strategy:
                    best_by_mutation[mutation_id] = {
                        "strategy": best_strategy,
                        "score": best_score
                    }
            
            comparison = {
                "ranking": ranking,
                "best_overall": ranking[0]["strategy"] if ranking else None,
                "best_by_mutation": best_by_mutation,
                "strategy_results": strategy_results,
                "simulation_summary": {
                    "mutations_analyzed": len(mutation_ids),
                    "successful_simulations": len([m for m in simulation_results if "error" not in simulation_results[m]])
                }
            }
            
            return comparison
        
        return {"error": "No valid strategy results generated"}