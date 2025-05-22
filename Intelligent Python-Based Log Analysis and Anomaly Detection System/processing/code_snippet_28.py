# Setup optimized parser infrastructure
format_cache = FormatCache(max_size=50000)
pattern_prefilter = PatternPrefilter()
ml_classifier = MLParserClassifier()
log_profiler = LogProfiler()

# Create base resolver with debugging capability
base_resolver = ParserResolver(debug=False, trace_all=False)

# Create optimized resolver using the cache and other optimizations
optimized_resolver = OptimizedParserResolver(base_resolver)

# Setup parallel processing
parallel_processor = ParallelLogProcessor(
    resolver=optimized_resolver,
    batch_size=1000,
    num_workers=8
)

# Example usage with asyncio
async def ingest_logs(log_source, output_queue):
    input_queue = asyncio.Queue(maxsize=10000)
    
    # Producer task
    async def producer():
        async for log_line in log_source:
            # Apply backpressure if queue is too full
            while input_queue.qsize() > 9000:
                await asyncio.sleep(0.1)
                
            await input_queue.put(log_line)
    
    # Start producer and processor
    producer_task = asyncio.create_task(producer())
    processor_task = asyncio.create_task(
        parallel_processor.process_stream(input_queue, output_queue)
    )
    
    # Wait for completion
    await asyncio.gather(producer_task, processor_task)