class OptimizedParserResolver:
    """Optimized parser resolver with multi-level caching."""
    
    def __init__(self, base_resolver: ParserResolver):
        self.base_resolver = base_resolver
        
        # Fast path: Format fingerprint cache
        self.format_cache = FormatCache(max_size=10000)
        
        # Medium path: ML-based classification
        self.ml_classifier = MLParserClassifier(training_threshold=2000)
        
        # Analytics
        self.stats = {
            "total": 0,
            "cache_hits": 0,
            "ml_hits": 0,
            "full_resolution": 0,
            "processing_time": 0.0
        }
    
    def resolve(self, log_line: str, chain_name: Optional[str] = None) -> ParsedLogEntry:
        """
        Resolve the best parser for a log line using a tiered approach:
        1. Try format cache (fastest)
        2. Try ML classification (medium)
        3. Fall back to full resolution (slowest)
        """
        import time
        start_time = time.time()
        
        self.stats["total"] += 1
        
        # Fast path: Try format cache
        cached_parser = self.format_cache.get(log_line)
        
        if cached_parser:
            # Attempt to parse with the cached parser
            parser_class = ParserRegistry.get_parser(cached_parser)
            if parser_class:
                parser = parser_class()
                entry = parser.parse(log_line)
                
                if entry and parser.validate(entry):
                    # Successful parse with cache hit
                    confidence = parser.confidence(log_line, entry)
                    
                    # Add parser metadata
                    entry.parser_metadata = {
                        "parser_name": cached_parser,
                        "confidence": confidence,
                        "resolution_path": "format_cache",
                        "processing_time_ms": (time.time() - start_time) * 1000
                    }
                    
                    self.stats["cache_hits"] += 1
                    self.stats["processing_time"] += time.time() - start_time
                    return entry
        
        # Medium path: Try ML classification
        if self.ml_classifier.trained:
            ml_parser = self.ml_classifier.predict(log_line)
            
            if ml_parser:
                parser_class = ParserRegistry.get_parser(ml_parser)
                if parser_class:
                    parser = parser_class()
                    entry = parser.parse(log_line)
                    
                    if entry and parser.validate(entry):
                        # Successful parse with ML prediction
                        confidence = parser.confidence(log_line, entry)
                        
                        # Update cache for next time
                        self.format_cache.update(log_line, ml_parser, confidence)
                        
                        # Add parser metadata
                        entry.parser_metadata = {
                            "parser_name": ml_parser,
                            "confidence": confidence,
                            "resolution_path": "ml_classifier",
                            "processing_time_ms": (time.time() - start_time) * 1000
                        }
                        
                        self.stats["ml_hits"] += 1
                        self.stats["processing_time"] += time.time() - start_time
                        return entry
        
        # Slow path: Full resolution
        entry, trace = self.base_resolver.resolve_with_trace(log_line, chain_name)
        
        if entry and trace.selected_parser:
            # Update format cache
            self.format_cache.update(log_line, trace.selected_parser, entry.confidence)
            
            # Add to ML training data
            self.ml_classifier.add_training_example(log_line, trace.selected_parser)
            
            # Add resolution path to metadata
            if "parser_metadata" not in entry or not isinstance(entry.parser_metadata, dict):
                entry.parser_metadata = {}
            
            entry.parser_metadata["resolution_path"] = "full_resolution"
            entry.parser_metadata["processing_time_ms"] = (time.time() - start_time) * 1000
            
            self.stats["full_resolution"] += 1
        
        self.stats["processing_time"] += time.time() - start_time
        return entry
    
    def get_stats(self) -> Dict[str, Any]:
        """Get resolver statistics."""
        stats = self.stats.copy()
        total = stats["total"]
        
        if total > 0:
            stats["cache_hit_rate"] = stats["cache_hits"] / total
            stats["ml_hit_rate"] = stats["ml_hits"] / total
            stats["full_resolution_rate"] = stats["full_resolution"] / total
            stats["avg_processing_time_ms"] = (stats["processing_time"] / total) * 1000
        else:
            stats["cache_hit_rate"] = 0
            stats["ml_hit_rate"] = 0
            stats["full_resolution_rate"] = 0
            stats["avg_processing_time_ms"] = 0
        
        # Add cache stats
        stats["format_cache"] = self.format_cache.get_stats()
        
        return stats