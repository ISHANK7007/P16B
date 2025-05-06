class ArbitrationWorker(Process):  # Could also use Thread
    """
    Worker process for evaluating conflict regions
    """
    def __init__(self, worker_id, task_queue, result_queue):
        super().__init__()
        self.worker_id = worker_id
        self.task_queue = task_queue
        self.result_queue = result_queue
        self.daemon = True  # Allow main process to exit even if workers are running
        
    def run(self):
        """Worker main loop"""
        while True:
            task = self.task_queue.get()
            
            # None is the signal to stop
            if task is None:
                break
                
            try:
                # Process the task
                result = self._process_task(task)
                
                # Send result back
                self.result_queue.put(result)
                
            except Exception as e:
                # Log error and continue
                print(f"Worker {self.worker_id} error: {str(e)}")
                # Could put error information in result queue
                
    def _process_task(self, task):
        """Process an arbitration task"""
        region_id = task["region_id"]
        proposals = task["proposals"]
        context = task["context"]
        evaluation_type = task.get("evaluation_type", "full")
        
        result = {
            "region_id": region_id,
            "scores": {},
            "metadata": {
                "worker_id": self.worker_id,
                "processing_time": 0,
                "evaluation_type": evaluation_type
            }
        }
        
        start_time = time.time()
        
        # Evaluate each proposal
        for proposal in proposals:
            if evaluation_type == "full":
                score = self._full_evaluation(proposal, context)
            elif evaluation_type == "fast":
                score = self._fast_evaluation(proposal, context)
            elif evaluation_type == "incremental":
                score = self._incremental_evaluation(proposal, task.get("previous_state"), context)
            else:
                score = self._full_evaluation(proposal, context)
                
            result["scores"][proposal.id] = {
                "value": score.value,
                "confidence": score.confidence,
                "components": score.components,
                "analysis": score.analysis
            }
            
        result["metadata"]["processing_time"] = time.time() - start_time
        
        return result
        
    def _full_evaluation(self, proposal, context):
        """Run full evaluation on a proposal"""
        # Implementation would use the constraint resolver to fully evaluate
        pass
        
    def _fast_evaluation(self, proposal, context):
        """Run a faster, approximate evaluation"""
        # Implementation would use heuristics for faster evaluation
        pass
        
    def _incremental_evaluation(self, proposal, previous_state, context):
        """Run incremental evaluation based on previous state"""
        # Implementation would only evaluate what changed
        pass