class PatternPrefilter:
    """Fast pre-filter to quickly eliminate incompatible parsers."""
    
    def __init__(self):
        self.parser_patterns = {}
        
    def register_parser(self, parser_name: str, quick_patterns: List[str]) -> None:
        """Register quick pattern checks for a parser."""
        self.parser_patterns[parser_name] = [re.compile(p) for p in quick_patterns]
    
    def get_candidate_parsers(self, log_line: str, max_prefix: int = 100) -> Set[str]:
        """Quickly identify candidate parsers for a log line."""
        prefix = log_line[:min(max_prefix, len(log_line))]
        candidates = set()
        
        for parser_name, patterns in self.parser_patterns.items():
            if any(p.search(prefix) for p in patterns):
                candidates.add(parser_name)
        
        return candidates