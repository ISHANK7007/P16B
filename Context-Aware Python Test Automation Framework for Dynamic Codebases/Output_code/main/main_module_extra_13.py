async def main():
    # Configure the simulator
    provider_configs = {
        LLMProvider.OPENAI_GPT4: {
            "model": "gpt-4",
            "requests_per_minute": 50,
            "max_parallel": 5
        },
        LLMProvider.ANTHROPIC_CLAUDE: {
            "model": "claude-2",
            "requests_per_minute": 40,
            "max_parallel": 4
        },
        LLMProvider.LOCAL_LLAMA: {
            "model_path": "./models/llama-7b",
            "max_parallel": x2
        }
    }
    
    # Create the simulator
    simulator = ParallelMutationSimulator(
        redis_url="redis://redis-master:6379/0",
        provider_configs=provider_configs
    )
    
    # Deploy workers
    await deploy_worker_cluster(simulator, total_workers=5)
    
    # Load mutations to simulate
    mutations = load_mutations_from_database()  # Hypothetical function
    
    # Deduplicate mutations
    deduplicated, duplication_map = await deduplicate_mutations(mutations)
    print(f"Reduced from {len(mutations)} to {len(deduplicated)} unique mutations")
    
    # Process the mutations
    batch_ids = await process_large_mutation_set(simulator, deduplicated)
    
    # Wait for all batches to complete
    results = []
    for batch_id in batch_ids:
        result = await simulator.wait_for_batch(batch_id, timeout=600)
        if result:
            results.append(result)
    
    # Analyze results
    total_mutations = sum(len(r.results) for r in results)
    successful = sum(sum(1 for m in r.results.values() if m.success) for r in results)
    
    print(f"Processed {total_mutations} mutations with {successful} successes")
    
    # Restore results for duplicated mutations
    for original_id, duplicate_of in duplication_map.items():
        # Find which batch contains the representative mutation
        for result in results:
            if duplicate_of in result.results:
                # Copy the result to the original ID
                duplicate_result = copy.deepcopy(result.results[duplicate_of])
                duplicate_result.mutation_id = original_id
                
                # Store it in the appropriate batch
                for r in results:
                    if original_id in [m.mutation_id for m in r.mutations]:
                        r.results[original_id] = duplicate_result
                        break
    
    # Clean up
    simulator.shutdown()

if __name__ == "__main__":
    asyncio.run(main())