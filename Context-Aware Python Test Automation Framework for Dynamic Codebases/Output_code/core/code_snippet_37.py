class TieredTokenCache:
    """
    Multi-level token cache with hot/warm/cold tiers to optimize
    memory usage while providing fast access for frequently accessed tokens.
    """
    def __init__(self, hot_size=1000, warm_size=10000, cold_size=100000):
        self.hot_cache = LRUCache(hot_size)  # L1: Very fast, in-memory
        self.warm_cache = SharedCache(warm_size)  # L2: Fast, shared memory
        self.cold_cache = DiskBackedCache(cold_size)  # L3: Slower, persistent
        self.stats = {
            "hot_hits": 0,
            "warm_hits": 0,
            "cold_hits": 0,
            "misses": 0
        }
        
    def get(self, key):
        """Retrieve a token with tiered caching"""
        # Try hot cache first
        value = self.hot_cache.get(key)
        if value is not None:
            self.stats["hot_hits"] += 1
            return value
            
        # Try warm cache
        value = self.warm_cache.get(key)
        if value is not None:
            # Promote to hot cache
            self.hot_cache.put(key, value)
            self.stats["warm_hits"] += 1
            return value
            
        # Try cold cache
        value = self.cold_cache.get(key)
        if value is not None:
            # Promote to warm cache
            self.warm_cache.put(key, value)
            self.stats["cold_hits"] += 1
            return value
            
        # Cache miss
        self.stats["misses"] += 1
        return None
        
    def put(self, key, value, priority=0):
        """Store a token with appropriate tier based on priority"""
        if priority > 0.7:
            # High priority goes to hot cache
            self.hot_cache.put(key, value)
        elif priority > 0.3:
            # Medium priority goes to warm cache
            self.warm_cache.put(key, value)
        else:
            # Low priority goes to cold cache
            self.cold_cache.put(key, value)