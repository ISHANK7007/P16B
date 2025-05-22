class HotpathOptimizer:
    """Optimize the most common parser execution paths."""
    
    def __init__(self, resolver: ParserResolver):
        self.resolver = resolver
        self.profiler = LogProfiler()
        self.specialized_parsers = {}
        
    def register_specialized_parser(self, parser_name: str, pattern: str, 
                                  specialized_func: Callable[[str], Optional[ParsedLogEntry]]) -> None:
        """Register a specialized fast-path function for a parser and pattern."""
        self.specialized_parsers[(parser_name, pattern)] = specialized_func
    
    def resolve(self, log_line: str) -> Optional[ParsedLogEntry]:
        """Try fast specialized paths first, then fall back to normal resolution."""
        # Try specialized parsers first
        for (parser_name, pattern), specialized_func in self.specialized_parsers.items():
            if re.search(pattern, log_line):
                try:
                    entry = specialized_func(log_line)
                    if entry:
                        return entry
                except Exception:
                    # Fall back to normal parser if specialized one fails
                    pass
        
        # Fall back to normal resolution
        entry, _ = self.resolver.resolve_with_trace(log_line)
        
        # Update profiler
        if entry and entry.parser_name:
            self.profiler.update(log_line, entry.parser_name)
            
        return entry