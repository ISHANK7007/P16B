class ConstraintEvaluationCache:
    """Caches constraint evaluation results across batches"""
    
    def __init__(self, redis_client=None):
        self.local_cache = {}
        self.redis = redis_client
    
    async def get_evaluation(self, 
                           constraint_id: str, 
                           content_hash: str) -> Optional[bool]:
        """Get cached constraint evaluation"""
        key = f"{constraint_id}:{content_hash}"
        
        # Check local cache
        if key in self.local_cache:
            return self.local_cache[key]
        
        # Check Redis
        if self.redis:
            value = self.redis.get(f"constraint:{key}")
            if value is not None:
                result = value == b'1'
                self.local_cache[key] = result
                return result
        
        return None
    
    async def store_evaluation(self, 
                            constraint_id: str, 
                            content_hash: str, 
                            result: bool):
        """Store constraint evaluation result"""
        key = f"{constraint_id}:{content_hash}"
        
        # Update local cache
        self.local_cache[key] = result
        
        # Update Redis
        if self.redis:
            self.redis.setex(
                f"constraint:{key}", 
                60 * 60 * 24,  # 24 hour TTL
                b'1' if result else b'0'
            )