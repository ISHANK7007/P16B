class TokenRewindScope:
    """Defines a scope for token rewinding with safety boundaries"""
    def __init__(self, start_idx, max_rewind_distance, dependencies=None):
        self.start_idx = start_idx
        self.max_rewind_distance = max_rewind_distance
        self.dependencies = dependencies or []
        self.safe_checkpoints = []
        
    def register_checkpoint(self, token_idx, state_snapshot):
        """Register a point that's safe to rewind to"""
        self.safe_checkpoints.append({
            "index": token_idx,
            "snapshot": state_snapshot,
            "affected_concepts": []
        })
        
    def can_rewind_to(self, target_idx):
        """Check if rewinding to this index is safe"""
        if target_idx < self.start_idx - self.max_rewind_distance:
            return False, "Beyond maximum rewind distance"
            
        # Check for checkpoint safety
        checkpoint = self._find_nearest_checkpoint(target_idx)
        if not checkpoint:
            return False, "No safe checkpoint found"
            
        return True, checkpoint