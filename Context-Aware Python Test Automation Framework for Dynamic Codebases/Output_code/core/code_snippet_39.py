class AdaptiveWorkerPool:
    """
    Worker pool that adjusts its size based on current workload
    to optimize resource usage for edit processing.
    """
    def __init__(self, min_workers=2, max_workers=20, target_queue_size=10):
        self.min_workers = min_workers
        self.max_workers = max_workers
        self.target_queue_size = target_queue_size
        self.current_workers = min_workers
        self.worker_tasks = []
        self.task_queue = asyncio.Queue()
        self.running = False
        self.stats = {
            "tasks_processed": 0,
            "peak_workers": min_workers,
            "scale_up_events": 0,
            "scale_down_events": 0
        }
        
    async def start(self):
        """Start the worker pool"""
        self.running = True
        
        # Create initial workers
        for _ in range(self.min_workers):
            self._add_worker()
            
        # Start autoscaler
        asyncio.create_task(self._auto_scale())
        
    def _add_worker(self):
        """Add a new worker to the pool"""
        if self.current_workers >= self.max_workers:
            return False
            
        task = asyncio.create_task(self._worker_loop())
        self.worker_tasks.append(task)
        self.current_workers += 1
        
        # Update stats
        self.stats["peak_workers"] = max(
            self.stats["peak_workers"], 
            self.current_workers
        )
        
        return True
        
    async def _remove_worker(self):
        """Remove a worker from the pool"""
        if self.current_workers <= self.min_workers:
            return False
            
        # Add a sentinel to signal worker to exit
        await self.task_queue.put(None)
        self.current_workers -= 1
        self.stats["scale_down_events"] += 1
        
        return True
        
    async def _worker_loop(self):
        """Worker loop for processing tasks"""
        while self.running:
            task = await self.task_queue.get()
            
            if task is None:
                # Exit signal
                self.task_queue.task_done()
                break
                
            try:
                await task["function"](*task["args"], **task["kwargs"])
                self.stats["tasks_processed"] += 1
            except Exception as e:
                # Log the error
                print(f"Worker error: {e}")
            finally:
                self.task_queue.task_done()
                
    async def _auto_scale(self):
        """Automatically scale the worker pool based on queue size"""
        while self.running:
            current_queue_size = self.task_queue.qsize()
            
            if current_queue_size > self.target_queue_size * 2:
                # Queue growing too large, add workers
                workers_to_add = min(
                    self.max_workers - self.current_workers,
                    (current_queue_size // self.target_queue_size) - 1
                )
                
                if workers_to_add > 0:
                    for _ in range(workers_to_add):
                        self._add_worker()
                    self.stats["scale_up_events"] += 1
                    
            elif current_queue_size < self.target_queue_size // 2:
                # Queue too small, can remove workers
                if self.current_workers > self.min_workers:
                    # Remove up to 25% of current workers, but keep at least min_workers
                    workers_to_remove = min(
                        self.current_workers - self.min_workers,
                        max(1, self.current_workers // 4)
                    )
                    
                    for _ in range(workers_to_remove):
                        await self._remove_worker()
                        
            # Check again after a delay
            await asyncio.sleep(5)