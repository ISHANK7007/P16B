class NormalizingLogParser(LogParser):
    """Decorator parser that normalizes the output of another parser."""
    
    def __init__(self, base_parser: LogParser, normalization_manager: LogNormalizationManager):
        self.base_parser = base_parser
        self.normalization_manager = normalization_manager
    
    def parse(self, log_line: str) -> Optional[ParsedLogEntry]:
        """Parse a log line and normalize the result."""
        # Parse with the base parser
        entry = self.base_parser.parse(log_line)
        
        if not entry:
            return None
            
        # Convert entry to dict for normalization
        entry_dict = entry.to_dict()
        
        # Add parser information if not present
        if "_parser" not in entry_dict:
            entry_dict["_parser"] = {"name": self.base_parser.name}
        
        # Normalize the entry
        normalized = self.normalization_manager.normalize(entry_dict)
        
        # Create a new ParsedLogEntry from normalized data
        result = ParsedLogEntry(
            timestamp=normalized["timestamp"],
            level=normalized["level"],
            message=normalized["message"],
            source=normalized.get("source", ""),
            fields={k: v for k, v in normalized.items() 
                   if k not in ["timestamp", "level", "message", "source"]}
        )
        
        # Preserve parser metadata
        if hasattr(entry, "parser_metadata"):
            result.parser_metadata = entry.parser_metadata
        
        return result

class NormalizingParserResolver:
    """Decorator for ParserResolver that applies normalization to results."""
    
    def __init__(self, base_resolver: ParserResolver, 
                normalization_manager: LogNormalizationManager):
        self.base_resolver = base_resolver
        self.normalization_manager = normalization_manager
    
    def resolve_with_trace(self, log_line: str, 
                         chain_name: Optional[str] = None,
                         force_trace: bool = False) -> Tuple[Optional[ParsedLogEntry], ParserTrace]:
        """Resolve the parser and normalize the result."""
        # Use the base resolver
        entry, trace = self.base_resolver.resolve_with_trace(log_line, chain_name, force_trace)
        
        if not entry:
            return None, trace
            
        # Convert entry to dict for normalization
        entry_dict = entry.to_dict()
        
        # Add parser information if not present
        if "_parser" not in entry_dict and trace.selected_parser:
            entry_dict["_parser"] = {"name": trace.selected_parser}
        
        # Normalize the entry
        normalized = self.normalization_manager.normalize(entry_dict)
        
        # Create a new ParsedLogEntry from normalized data
        result = ParsedLogEntry(
            timestamp=normalized["timestamp"],
            level=normalized["level"],
            message=normalized["message"],
            source=normalized.get("source", ""),
            fields={k: v for k, v in normalized.items() 
                   if k not in ["timestamp", "level", "message", "source"]}
        )
        
        # Preserve parser metadata
        if hasattr(entry, "parser_metadata"):
            result.parser_metadata = entry.parser_metadata
            
            # Add normalization info to metadata
            result.parser_metadata["normalized"] = True
        
        return result, trace