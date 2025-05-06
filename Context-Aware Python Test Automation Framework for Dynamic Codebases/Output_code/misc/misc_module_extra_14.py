async def optimize_resource_allocation(simulator):
    """Dynamically adjust resource allocation based on workload"""
    while True:
        # Analyze current workload
        queue_stats = await get_queue_statistics()  # Hypothetical function
        
        # Adjust container resources based on workload type
        if queue_stats['json_mutations'] > queue_stats['text_mutations'] * 3:
            # Heavy JSON workload - allocate more resources to GPT-4 workers
            for i in range(3):
                simulator.worker_manager.start_worker(
                    f"gpt4_surge_{i}", [LLMProvider.OPENAI_GPT4]
                )
        
        # Scale down underutilized resources
        for worker_id, stats in queue_stats['worker_stats'].items():
            if stats['utilization'] < 0.3 and stats['idle_time'] > 300:
                simulator.worker_manager.stop_worker(worker_id)
        
        await asyncio.sleep(300)  # Check every 5 minutes