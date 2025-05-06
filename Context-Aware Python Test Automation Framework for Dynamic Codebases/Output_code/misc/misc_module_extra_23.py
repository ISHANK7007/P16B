async def analyze_prompt_mutation_divergence(mutation_id: str):
    """Example of analyzing persona divergence for a single mutation"""
    # Configure personas
    personas = {
        "expert_json": Persona(
            type=PersonaType.EXPERT,
            name="JSON Expert",
            expertise=["JSON", "API Design"],
            mutation_style="Technical and precise",
            context_depth=5
        ),
        "creative_writer": Persona(
            type=PersonaType.CREATIVE,
            name="Creative Writer",
            expertise=["Content Creation", "Storytelling"],
            mutation_style="Elaborate and descriptive",
            context_depth=3
        ),
        "safety_focused": Persona(
            type=PersonaType.SAFETY_FOCUSED,
            name="Safety Guardian",
            expertise=["Content Moderation", "Safe Design"],
            mutation_style="Cautious and thorough",
            context_depth=4
        ),
        "analytical": Persona(
            type=PersonaType.ANALYTICAL,
            name="Data Analyst",
            expertise=["Data Schema", "Analytics"],
            mutation_style="Structured and systematic",
            context_depth=4
        ),
        "generalist": Persona(
            type=PersonaType.GENERALIST,
            name="General Assistant",
            expertise=["General Knowledge"],
            mutation_style="Balanced and adaptive",
            context_depth=3
        )
    }

    # Initialize engine with personas
    replay_engine = EnhancedMutationReplayEngine(
        model_registry={},  # Would fill with actual models
        constraint_registry={},  # Would fill with actual constraints
        sandbox_factory=lambda m, c: None  # Simplified for example
    )
    
    # Initialize persona components
    replay_engine.initialize_persona_components(personas)
    
    # Get the trace for the mutation
    trace = replay_engine.trace_repository.get(mutation_id)
    if not trace:
        print(f"Trace {mutation_id} not found")
        return
        
    # Simulate with all personas
    print(f"Simulating mutation {mutation_id} with all personas...")
    result = await replay_engine.persona_simulator.simulate_with_personas(trace)
    
    if "error" in result:
        print(f"Error: {result['error']}")
        return
        
    # Generate divergence report
    print("Generating divergence report...")
    divergence_report = await replay_engine.persona_simulator.generate_divergence_report(
        mutation_id=mutation_id,
        include_visualization=True
    )
    
    # Output key metrics
    entropy = divergence_report.get("entropy", 0)
    agreement = divergence_report.get("agreement_rate", 0)
    clusters = len(divergence_report.get("decision_clusters", []))
    
    print(f"Divergence Analysis Results:")
    print(f"- Entropy: {entropy:.3f} (higher = more diverse decisions)")
    print(f"- Agreement Rate: {agreement:.2f} (higher = more consensus)")
    print(f"- Decision Clusters: {clusters} (higher = more distinct approaches)")
    
    # Compare with actual arbitration result
    # For this example, let's assume we have the historical arbitration result
    historical_arbitration = PromptMutation(
        original=trace.original_prompt,
        mutated=trace.mutated_prompt,
        format=trace.prompt_format,
        mutation_rationale="Historical arbitration result"
    )
    
    # Score the historical arbitration
    print("Scoring historical arbitration result...")
    arbitration_metrics = await replay_engine.arbitration_scorer.score_arbitration_with_divergence(
        mutation_id=mutation_id,
        arbitration_result=historical_arbitration
    )
    
    print(f"Arbitration Analysis Results:")
    print(f"- Score: {arbitration_metrics.get('arbitration_score', 0):.3f}")
    print(f"- Category: {arbitration_metrics.get('arbitration_category', 'Unknown')}")
    print(f"- Supporting Personas: {len(arbitration_metrics.get('supporting_personas', []))}")
    
    # Compare different arbitration strategies
    print("Comparing arbitration strategies...")
    
    # Define some example strategies
    strategies = {
        "Majority Vote": lambda mutations: sorted(
            mutations, 
            key=lambda m: sum(1 for other in mutations if other.mutated == m.mutated),
            reverse=True
        )[0],
        
        "Expert Priority": lambda mutations: sorted(
            mutations,
            # This assumes each mutation has a persona_type attribute
            # Would need to be added in real implementation
            key=lambda m: m.metadata.get("persona_type") == PersonaType.EXPERT,
            reverse=True
        )[0],
        
        "Consensus Seeking": lambda mutations: sorted(
            mutations,
            # Find mutation with highest average similarity to all others
            key=lambda m1: sum(
                SequenceMatcher(None, m1.mutated, m2.mutated).ratio()
                for m2 in mutations
            ) / len(mutations),
            reverse=True
        )[0]
    }
    
    strategy_comparison = await replay_engine.compare_arbitration_strategies(
        mutation_ids=[mutation_id],
        strategies=strategies
    )
    
    if "error" not in strategy_comparison:
        print("Strategy Ranking:")
        for rank in strategy_comparison["ranking"]:
            print(f"- {rank['strategy']}: {rank['score']:.3f}")
    
    return divergence_report, arbitration_metrics, strategy_comparison