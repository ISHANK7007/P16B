@dataclass
class ParsedLogEntry:
    """Enhanced parsed log entry with trace information."""
    timestamp: datetime
    level: str = "INFO"
    message: str = ""
    source: str = ""
    fields: Dict[str, Any] = field(default_factory=dict)
    
    # New metadata fields for debugging and auditing
    parser_metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def parser_name(self) -> Optional[str]:
        """Get the name of the parser that produced this entry."""
        return self.parser_metadata.get("parser_name")
    
    @property
    def confidence(self) -> float:
        """Get the confidence score for this parsed entry."""
        return self.parser_metadata.get("confidence", 0.0)
    
    @property
    def has_trace(self) -> bool:
        """Check if this entry has a parser trace."""
        return "trace_id" in self.parser_metadata
    
    @property
    def trace_id(self) -> Optional[str]:
        """Get the trace ID for this entry."""
        return self.parser_metadata.get("trace_id")
    
    @property 
    def parsing_conflicts(self) -> bool:
        """Check if there were parsing conflicts for this log line."""
        return self.parser_metadata.get("conflicts_detected", False)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the log entry to a dictionary."""
        result = {
            "timestamp": self.timestamp.isoformat(),
            "level": self.level,
            "message": self.message, 
            "source": self.source,
            **self.fields
        }
        
        # Include parser metadata if requested
        if self.parser_metadata:
            result["_parser"] = {
                "name": self.parser_name,
                "confidence": round(self.confidence, 4)
            }
            
            # Include conflicts information if present
            if self.parsing_conflicts:
                result["_parser"]["conflicts"] = True
                
            # Include trace ID if present
            if self.has_trace:
                result["_parser"]["trace_id"] = self.trace_id
                
        return result