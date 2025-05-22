from typing import Dict, Optional, Tuple, List, Set, Callable
import re
import hashlib
from functools import lru_cache
from collections import defaultdict, Counter

class ParserFingerprint:
    """A fingerprint of a log line used for parser matching."""
    
    def __init__(self, prefix_length: int = 20, use_regex_groups: bool = True):
        self.prefix_length = prefix_length
        self.use_regex_groups = use_regex_groups
        
    def generate(self, log_line: str) -> str:
        """Generate a fingerprint for a log line."""
        # Start with a basic prefix fingerprint
        if not log_line:
            return ""
            
        # Use prefix as base fingerprint
        prefix = log_line[:min(self.prefix_length, len(log_line))]
        
        # Normalize the prefix for better grouping
        # Replace digits with 'd', lowercase letters with 'c', uppercase with 'C'
        normalized = re.sub(r'[0-9]', 'd', prefix)
        normalized = re.sub(r'[a-z]', 'c', normalized)
        normalized = re.sub(r'[A-Z]', 'C', normalized)
        
        # Extract structural patterns
        # e.g., ISO timestamps, brackets, IP addresses, etc.
        patterns = []
        
        if '[' in prefix:
            patterns.append('has_brackets')
        
        if re.search(r'\d{4}-\d{2}-\d{2}', log_line[:30]):
            patterns.append('has_iso_date')
        
        if re.search(r'\d{2}:\d{2}:\d{2}', log_line[:30]):
            patterns.append('has_time')
        
        if re.search(r'\d+\.\d+\.\d+\.\d+', log_line[:40]):
            patterns.append('has_ip')
        
        # Create a composite fingerprint
        fingerprint = f"{normalized}|{'|'.join(sorted(patterns))}"
        return fingerprint
    
    @lru_cache(maxsize=1000)
    def extract_groups(self, log_line: str, max_length: int = 100) -> Dict[str, str]:
        """Extract regex groups from a log line for more detailed fingerprinting."""
        if not self.use_regex_groups or not log_line:
            return {}
        
        sample = log_line[:min(max_length, len(log_line))]
        groups = {}
        
        # Common regex patterns in log lines
        patterns = [
            # ISO timestamp
            (r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:[+-]\d{2}:?\d{2}|Z)?)', 'timestamp'),
            # Common timestamp formats
            (r'(\d{2}/\w{3}/\d{4}:\d{2}:\d{2}:\d{2} [+-]\d{4})', 'timestamp_apache'),
            # Log level
            (r'\b(DEBUG|INFO|WARN(?:ING)?|ERROR|CRITICAL|FATAL)\b', 'level'),
            # IP address
            (r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', 'ip'),
            # Process ID
            (r'\[(\d+)\]', 'pid'),
            # Single-word component in brackets
            (r'\[(\w+)\]', 'component')
        ]
        
        for pattern, name in patterns:
            match = re.search(pattern, sample)
            if match:
                groups[name] = match.group(1)
        
        return groups

class FormatCache:
    """Cache for mapping log fingerprints to the most successful parsers."""
    
    def __init__(self, 
                max_size: int = 10000,
                fingerprinter: Optional[ParserFingerprint] = None,
                min_confidence: float = 0.7,
                ttl_seconds: int = 3600):
        self.cache: Dict[str, CacheEntry] = {}
        self.fingerprinter = fingerprinter or ParserFingerprint()
        self.max_size = max_size
        self.min_confidence = min_confidence
        self.ttl_seconds = ttl_seconds
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        
    class CacheEntry:
        """Entry in the format cache."""
        
        def __init__(self, parser_name: str, confidence: float, timestamp: float):
            self.parser_name = parser_name
            self.confidence = confidence
            self.timestamp = timestamp
            self.hits = 1
            self.total_confidence = confidence
            self.last_used = timestamp
        
        def update(self, parser_name: str, confidence: float, timestamp: float) -> None:
            """Update cache entry with new information."""
            # Don't update if the new parser has significantly lower confidence
            if self.confidence > confidence + 0.2:
                return
                
            if confidence > self.confidence:
                self.parser_name = parser_name
                self.confidence = confidence
            
            self.hits += 1
            self.total_confidence += confidence
            self.last_used = timestamp
    
    def get(self, log_line: str) -> Optional[str]:
        """Get the best parser name for a log line using its fingerprint."""
        import time
        
        fingerprint = self.fingerprinter.generate(log_line)
        current_time = time.time()
        
        # Check if we have a cache entry and it's not expired
        if fingerprint in self.cache:
            entry = self.cache[fingerprint]
            
            # Check if the entry is expired
            if current_time - entry.timestamp > self.ttl_seconds:
                del self.cache[fingerprint]
                self.misses += 1
                return None
            
            # Update usage statistics
            entry.last_used = current_time
            self.hits += 1
            
            return entry.parser_name
        
        self.misses += 1
        return None
    
    def update(self, log_line: str, parser_name: str, confidence: float) -> None:
        """Update the cache with a successful parse result."""
        import time
        
        # Only cache results with good confidence
        if confidence < self.min_confidence:
            return
        
        fingerprint = self.fingerprinter.generate(log_line)
        current_time = time.time()
        
        # Update existing entry or create a new one
        if fingerprint in self.cache:
            self.cache[fingerprint].update(parser_name, confidence, current_time)
        else:
            # Check if we need to evict an entry
            if len(self.cache) >= self.max_size:
                self._evict_entry()
            
            self.cache[fingerprint] = self.CacheEntry(parser_name, confidence, current_time)
    
    def _evict_entry(self) -> None:
        """Evict an entry from the cache using a combined strategy."""
        import time
        
        current_time = time.time()
        
        # Strategy: Consider least recently used and lowest confidence
        # This creates a score that balances recency and quality
        worst_score = float('inf')
        worst_key = None
        
        for key, entry in self.cache.items():
            # Calculate age factor (0 to 1, older is higher)
            age_factor = min(1.0, (current_time - entry.last_used) / self.ttl_seconds)
            
            # Calculate a score - lower is worse
            # This combines age and confidence
            score = (1 - age_factor) + entry.confidence
            
            if score < worst_score:
                worst_score = score
                worst_key = key
        
        if worst_key:
            del self.cache[worst_key]
            self.evictions += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self.hits + self.misses
        hit_rate = self.hits / total_requests if total_requests > 0 else 0
        
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hit_rate": hit_rate,
            "hits": self.hits,
            "misses": self.misses,
            "evictions": self.evictions
        }
    
    def get_most_common_fingerprints(self, n: int = 10) -> List[Tuple[str, int]]:
        """Get the most commonly hit fingerprints."""
        # Sort by hits
        sorted_entries = sorted(
            [(k, v.hits) for k, v in self.cache.items()],
            key=lambda x: x[1],
            reverse=True
        )
        
        return sorted_entries[:n]

class GroupFingerprint:
    """Advanced fingerprinting that groups similar log formats."""
    
    def __init__(self, n_features: int = 5, prefix_length: int = 30):
        self.n_features = n_features
        self.prefix_length = prefix_length
    
    def _extract_features(self, log_line: str) -> List[str]:
        """Extract key features from a log line."""
        features = []
        
        # Keep only the prefix for efficiency
        prefix = log_line[:min(self.prefix_length, len(log_line))]
        
        # Extract structural features
        # 1. Character class distribution
        char_classes = {
            'digit': sum(1 for c in prefix if c.isdigit()),
            'upper': sum(1 for c in prefix if c.isupper()),
            'lower': sum(1 for c in prefix if c.islower()),
            'punct': sum(1 for c in prefix if not c.isalnum() and not c.isspace())
        }
        
        # Normalize to percentage of length
        length = len(prefix)
        for k, v in char_classes.items():
            features.append(f"{k}_{int(v/length*10)}")
        
        # 2. Specific tokens/patterns
        patterns = [
            ('has_iso8601', r'\d{4}-\d{2}-\d{2}'),
            ('has_time', r'\d{2}:\d{2}:\d{2}'),
            ('has_brackets', r'\[.*?\]'),
            ('has_parentheses', r'\(.*?\)'),
            ('has_equals', r'='),
            ('has_ip', r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}')
        ]
        
        for name, pattern in patterns:
            if re.search(pattern, prefix):
                features.append(name)
        
        # 3. Position of first special characters
        special_chars = ['{', '[', '(', ':', '=']
        for char in special_chars:
            pos = prefix.find(char)
            if pos != -1:
                features.append(f"first_{char}_{pos//5*5}")
        
        # 4. Token structure (simplified)
        token_structure = []
        for token in re.findall(r'\S+', prefix):
            if token.isdigit():
                token_structure.append('d')
            elif token.isalpha():
                if token.isupper():
                    token_structure.append('U')
                elif token.islower():
                    token_structure.append('l')
                else:
                    token_structure.append('m')  # mixed case
            elif all(not c.isalnum() for c in token):
                token_structure.append('p')  # punctuation
            else:
                token_structure.append('x')  # mixed
        
        if token_structure:
            features.append('tokens_' + ''.join(token_structure[:5]))
        
        return features
    
    def generate(self, log_line: str) -> str:
        """Generate a fingerprint that groups similar log formats."""
        features = self._extract_features(log_line)
        
        # Take the top N most important features
        top_features = sorted(features)[:self.n_features]
        
        return '|'.join(top_features)