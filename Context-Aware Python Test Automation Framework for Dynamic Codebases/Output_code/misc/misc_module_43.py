class BatchScoreAggregator:
    """
    Aggregates scores across batches of evaluations with streaming support
    """
    def __init__(self, aggregation_strategy="weighted_average"):
        self.aggregation_strategy = aggregation_strategy
        self.partial_results = {}  # Maps region_id to partial results
        self.completion_status = {}  # Maps region_id to completion percentage
        self.batch_listeners = []  # Callbacks for batch completion events
        
    def create_batch(self, region_id, expected_evaluations):
        """
        Initialize a new scoring batch
        Returns a BatchHandle for adding scores
        """
        self.partial_results[region_id] = {
            "scores": {},
            "metadata": {},
            "expected_count": expected_evaluations,
            "received_count": 0,
            "start_time": time.time()
        }
        
        self.completion_status[region_id] = 0.0
        
        return BatchHandle(region_id, self)
        
    def add_score(self, region_id, proposal_id, score_data):
        """
        Add a score to a batch
        Returns updated completion percentage
        """
        if region_id not in self.partial_results:
            return 0.0
            
        batch = self.partial_results[region_id]
        
        # Add or update score
        batch["scores"][proposal_id] = score_data
        
        # Update completion status
        batch["received_count"] += 1
        completion = min(1.0, batch["received_count"] / max(1, batch["expected_count"]))
        self.completion_status[region_id] = completion
        
        # Notify listeners if batch is complete
        if completion >= 1.0:
            self._notify_batch_complete(region_id)
            
        return completion
        
    def get_aggregate_scores(self, region_id):
        """
        Get aggregated scores for a region
        Works with partial results if not all scores are in
        """
        if region_id not in self.partial_results:
            return None
            
        batch = self.partial_results[region_id]
        
        if not batch["scores"]:
            return None
            
        # Apply the selected aggregation strategy
        if self.aggregation_strategy == "weighted_average":
            return self._aggregate_weighted_average(batch["scores"])
        elif self.aggregation_strategy == "rank_based":
            return self._aggregate_rank_based(batch["scores"])
        else:
            # Default to simple average
            return self._aggregate_simple_average(batch["scores"])
            
    def get_completion_status(self, region_id):
        """Get the completion status of a batch"""
        if region_id in self.completion_status:
            return self.completion_status[region_id]
        return 0.0
        
    def add_batch_listener(self, listener):
        """Add a listener for batch completion events"""
        self.batch_listeners.append(listener)
        
    def _notify_batch_complete(self, region_id):
        """Notify listeners that a batch is complete"""
        for listener in self.batch_listeners:
            listener(region_id, self.partial_results[region_id])
            
    def _aggregate_weighted_average(self, scores):
        """Aggregate scores using weighted average"""
        # Implementation would compute weighted average based on
        # score confidence, evaluator trust, etc.
        pass
        
    def _aggregate_rank_based(self, scores):
        """Aggregate scores using rank-based methods"""
        # Implementation would use ranking algorithms like Borda count
        # to aggregate scores
        pass
        
    def _aggregate_simple_average(self, scores):
        """Aggregate scores using simple average"""
        # Simple implementation as fallback
        result = {}
        
        for proposal_id, score_data in scores.items():
            if "value" in score_data:
                if proposal_id not in result:
                    result[proposal_id] = {
                        "sum": 0,
                        "count": 0
                    }
                result[proposal_id]["sum"] += score_data["value"]
                result[proposal_id]["count"] += 1
                
        # Compute averages
        averages = {}
        for proposal_id, data in result.items():
            if data["count"] > 0:
                averages[proposal_id] = data["sum"] / data["count"]
                
        return averages