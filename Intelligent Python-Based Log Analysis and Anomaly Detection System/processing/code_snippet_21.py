import asyncio
import multiprocessing
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor

class ParallelLogProcessor:
    """Parallel log processing pipeline for high-volume log ingestion."""
    
    def __init__(self, 
                resolver: OptimizedParserResolver,
                batch_size: int = 1000,
                num_workers: int = None):
        self.resolver = resolver
        self.batch_size = batch_size
        self.num_workers = num_workers or max(1, multiprocessing.cpu_count() - 1)
        self.executor = ThreadPoolExecutor(max_workers=self.num_workers)
    
    async def process_batch(self, logs: List[str]) -> List[ParsedLogEntry]:
        """Process a batch of logs in parallel."""
        loop = asyncio.get_event_loop()
        
        # Split the work
        future_to_log = {}
        for log_line in logs:
            future = loop.run_in_executor(
                self.executor,
                self.resolver.resolve,
                log_line
            )
            future_to_log[future] = log_line
        
        # Gather results
        results = []
        for future in asyncio.as_completed(future_to_log):
            entry = await future
            if entry:
                results.append(entry)
        
        return results
    
    async def process_stream(self, 
                           log_stream: asyncio.Queue, 
                           output_stream: asyncio.Queue) -> None:
        """Process a stream of logs in batched parallel fashion."""
        batch = []
        
        while True:
            # Collect a batch of logs
            try:
                log_line = await asyncio.wait_for(log_stream.get(), timeout=0.1)
                batch.append(log_line)
                log_stream.task_done()
            except asyncio.TimeoutError:
                # No more logs in the queue for now
                pass
            
            # Process batch if it's full or there's a timeout and batch isn't empty
            if len(batch) >= self.batch_size or (batch and len(batch) > 0):
                results = await self.process_batch(batch)
                
                # Put results in the output stream
                for entry in results:
                    await output_stream.put(entry)
                
                # Clear batch
                batch = []
            
            # Small pause to allow other tasks to run
            await asyncio.sleep(0.01)