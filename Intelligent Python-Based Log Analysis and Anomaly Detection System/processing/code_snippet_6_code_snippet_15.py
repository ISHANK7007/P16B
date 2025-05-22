from functools import lru_cache
from typing import Dict, List, Tuple, Set, Optional, Any
from datetime import datetime, timedelta
import time
import hashlib

class EscalationDecisionCache:
    """Cache for escalation decisions with TTL invalidation"""
    
    def __init__(self, default_ttl_seconds: int = 300, max_entries: int = 10000):
        self.cache: Dict[str, Tuple[Any, float]] = {}  # key -> (value, expiry)
        self.default_ttl = default_ttl_seconds
        self.max_entries = max_entries
        self.hits = 0
        self.misses = 0
        self.last_cleanup = time.time()
        self.cleanup_interval = 60  # Cleanup every 60 seconds
        
    def _generate_key(self, 
                     fingerprint: str, 
                     policy_id: str,
                     escalation_level: EscalationLevel) -> str:
        """Generate a cache key for the decision"""
        return f"{fingerprint}:{policy_id}:{escalation_level.name}"
    
    def get(self, 
           fingerprint: str, 
           policy_id: str,
           escalation_level: EscalationLevel) -> Optional[Dict]:
        """Get a cached decision if available and not expired"""
        key = self._generate_key(fingerprint, policy_id, escalation_level)
        
        # Perform occasional cleanup to prevent memory growth
        current_time = time.time()
        if current_time - self.last_cleanup > self.cleanup_interval:
            self._cleanup_expired()
            
        if key not in self.cache:
            self.misses += 1
            return None
            
        value, expiry = self.cache[key]
        
        # Check if expired
        if current_time > expiry:
            del self.cache[key]
            self.misses += 1
            return None
            
        self.hits += 1
        return value
    
    def set(self, 
           fingerprint: str, 
           policy_id: str,
           escalation_level: EscalationLevel,
           decision: Dict,
           ttl_seconds: Optional[int] = None) -> None:
        """Cache an escalation decision with expiry"""
        key = self._generate_key(fingerprint, policy_id, escalation_level)
        expiry = time.time() + (ttl_seconds or self.default_ttl)
        
        # If we're at capacity, remove oldest entry
        if len(self.cache) >= self.max_entries:
            self._remove_oldest_entry()
            
        self.cache[key] = (decision, expiry)
    
    def invalidate(self, 
                  fingerprint: Optional[str] = None, 
                  policy_id: Optional[str] = None) -> int:
        """Invalidate cache entries by fingerprint and/or policy"""
        count = 0
        keys_to_remove = []
        
        for key in self.cache.keys():
            parts = key.split(':')
            if len(parts) != 3:
                continue
                
            fp, pol, _ = parts
            
            if fingerprint and fp != fingerprint:
                continue
                
            if policy_id and pol != policy_id:
                continue
                
            keys_to_remove.append(key)
            
        for key in keys_to_remove:
            del self.cache[key]
            count += 1
            
        return count
    
    def _cleanup_expired(self) -> int:
        """Remove all expired entries from cache"""
        current_time = time.time()
        self.last_cleanup = current_time
        
        count = 0
        keys_to_remove = []
        
        for key, (_, expiry) in self.cache.items():
            if current_time > expiry:
                keys_to_remove.append(key)
                
        for key in keys_to_remove:
            del self.cache[key]
            count += 1
            
        return count
    
    def _remove_oldest_entry(self) -> None:
        """Remove the entry with the earliest expiry time"""
        if not self.cache:
            return
            
        oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k][1])
        del self.cache[oldest_key]
    
    def get_stats(self) -> Dict:
        """Get cache statistics"""
        total_requests = self.hits + self.misses
        hit_ratio = self.hits / total_requests if total_requests > 0 else 0
        
        return {
            "size": len(self.cache),
            "max_size": self.max_entries,
            "hit_ratio": hit_ratio,
            "hits": self.hits,
            "misses": self.misses
        }