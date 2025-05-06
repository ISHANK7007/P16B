class BatchHandle:
    """
    Handle for adding scores to a batch
    Provides a clean API and validation
    """
    def __init__(self, region_id, aggregator):
        self.region_id = region_id
        self.aggregator = aggregator
        
    def add_score(self, proposal_id, score_value, confidence=1.0, metadata=None):
        """Add a score to the batch"""
        score_data = {
            "value": score_value,
            "confidence": confidence,
            "timestamp": time.time(),
            "metadata": metadata or {}
        }
        
        return self.aggregator.add_score(self.region_id, proposal_id, score_data)
        
    def get_completion(self):
        """Get current completion status"""
        return self.aggregator.get_completion_status(self.region_id)
        
    def get_aggregate(self):
        """Get current aggregate scores"""
        return self.aggregator.get_aggregate_scores(self.region_id)