class ParallelArbitrationEngine:
    """
    Coordinates parallel processing of conflict regions
    using worker threads/processes
    """
    def __init__(self, worker_count=None, scheduler_strategy="dynamic"):
        self.worker_count = worker_count or min(10, max(1, os.cpu_count() - 1))
        self.scheduler_strategy = scheduler_strategy
        self.workers = []
        self.task_queue = Queue()
        self.result_queue = Queue()
        self.running = False
        self.scheduler = self._create_scheduler()
        
    def start(self):
        """Start the worker processes/threads"""
        if self.running:
            return
            
        self.running = True
        
        # Start workers
        for i in range(self.worker_count):
            worker = ArbitrationWorker(i, self.task_queue, self.result_queue)
            worker.start()
            self.workers.append(worker)
            
    def stop(self):
        """Stop all workers"""
        if not self.running:
            return
            
        # Signal all workers to stop
        for _ in range(self.worker_count):
            self.task_queue.put(None)  # None is the stop signal
            
        # Wait for all workers to finish
        for worker in self.workers:
            worker.join()
            
        self.workers = []
        self.running = False
        
    def process_regions(self, conflict_regions, context, score_aggregator):
        """
        Process conflict regions in parallel
        Returns a Future object for getting results
        """
        if not self.running:
            self.start()
            
        # Create task descriptors
        tasks = self.scheduler.schedule_tasks(conflict_regions, context)
        
        # Create future for tracking results
        future = ArbitrationFuture(
            [region.id for region in conflict_regions], 
            score_aggregator
        )
        
        # Start result collector thread
        collector = threading.Thread(
            target=self._collect_results,
            args=(future, len(tasks), self.result_queue)
        )
        collector.daemon = True
        collector.start()
        
        # Submit tasks to queue
        for task in tasks:
            self.task_queue.put(task)
            
        return future
        
    def _collect_results(self, future, expected_count, result_queue):
        """Collect and process results from workers"""
        received = 0
        
        while received < expected_count:
            try:
                result = result_queue.get(timeout=30)  # 30-second timeout
                if result is not None:
                    future.add_result(result)
                    received += 1
            except queue.Empty:
                # Check if we should continue waiting
                if not self.running:
                    break
                    
        future.set_complete()
        
    def _create_scheduler(self):
        """Create the appropriate task scheduler"""
        if self.scheduler_strategy == "dynamic":
            return DynamicTaskScheduler()
        elif self.scheduler_strategy == "priority":
            return PriorityTaskScheduler()
        elif self.scheduler_strategy == "static":
            return StaticTaskScheduler(self.worker_count)
        else:
            return DynamicTaskScheduler()  # Default