class LogProfiler:
    """Profile log sources to optimize parser selection."""
    
    def __init__(self, window_size: int = 10000):
        self.window_size = window_size
        self.parser_histogram = Counter()
        self.format_histogram = Counter()
        self.total_logs = 0
        
    def update(self, log_line: str, parser_name: str) -> None:
        """Update profiling information."""
        self.total_logs += 1
        self.parser_histogram[parser_name] += 1
        
        # Use a fingerprint for format tracking
        fingerprinter = ParserFingerprint(prefix_length=30)
        fingerprint = fingerprinter.generate(log_line)
        self.format_histogram[fingerprint] += 1
        
        # Reset histograms if we've exceeded the window size
        if self.total_logs > self.window_size:
            # Reduce the counts but keep the distribution
            for key in self.parser_histogram:
                self.parser_histogram[key] //= 2
            
            for key in self.format_histogram:
                self.format_histogram[key] //= 2
            
            self.total_logs //= 2
    
    def get_most_likely_parsers(self, n: int = 3) -> List[str]:
        """Get the most likely parsers based on historical data."""
        return [parser for parser, _ in self.parser_histogram.most_common(n)]
    
    def get_format_distribution(self) -> Dict[str, float]:
        """Get the distribution of log formats."""
        total = sum(self.format_histogram.values())
        if total == 0:
            return {}
            
        return {fmt: count/total for fmt, count in self.format_histogram.most_common(20)}