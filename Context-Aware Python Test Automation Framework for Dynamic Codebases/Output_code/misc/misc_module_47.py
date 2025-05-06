class ArbitrationFuture:
    """
    Future object for tracking asynchronous arbitration results
    """
    def __init__(self, region_ids, score_aggregator):
        self.region_ids = set(region_ids)
        self.score_aggregator = score_aggregator
        self.complete = False
        self.completed_regions = set()
        self.condition = threading.Condition()
        self.final_results = None
        
    def add_result(self, result):
        """Add a result from a worker"""
        region_id = result["region_id"]
        
        # Add scores to aggregator
        for proposal_id, score_data in result["scores"].items():
            batch = self.score_aggregator.create_batch(region_id, 1)
            batch.add_score(
                proposal_id,
                score_data["value"],
                score_data.get("confidence", 1.0),
                score_data
            )
            
        with self.condition:
            self.completed_regions.add(region_id)
            self.condition.notify_all()
            
    def set_complete(self):
        """Mark the future as complete"""
        with self.condition:
            self.complete = True
            self.condition.notify_all()
            
    def done(self):
        """Check if all regions are processed"""
        with self.condition:
            return self.complete and self.completed_regions >= self.region_ids
            
    def result(self, timeout=None):
        """
        Get the final results, waiting if necessary
        Returns the aggregated scores for all regions
        """
        if not self.done() and timeout != 0:
            with self.condition:
                self.condition.wait(timeout)
                
        if not self.done():
            raise TimeoutError("ArbitrationFuture timed out waiting for results")
            
        if not self.final_results:
            # Combine results from all regions
            self.final_results = self._combine_region_results()
            
        return self.final_results
        
    def get_completion_percentage(self):
        """Get overall completion percentage"""
        if self.done():
            return 1.0
            
        total_regions = len(self.region_ids)
        if total_regions == 0:
            return 1.0
            
        completed = len(self.completed_regions)
        partial = 0.0
        
        # Add partial completion from incomplete regions
        for region_id in self.region_ids - self.completed_regions:
            partial += self.score_aggregator.get_completion_status(region_id)
            
        return (completed + partial) / total_regions
        
    def _combine_region_results(self):
        """Combine results from all regions into a final result"""
        combined = {}
        
        for region_id in self.region_ids:
            region_scores = self.score_aggregator.get_aggregate_scores(region_id)
            
            if region_scores:
                for proposal_id, score in region_scores.items():
                    if proposal_id not in combined:
                        combined[proposal_id] = []
                    combined[proposal_id].append(score)
                    
        # Average scores across regions for proposals that appear in multiple regions
        final_scores = {}
        for proposal_id, scores in combined.items():
            final_scores[proposal_id] = sum(scores) / len(scores)
            
        return final_scores