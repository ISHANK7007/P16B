class LogParser(ABC):
    """Enhanced base interface for all log parsers with validation and confidence scoring."""
    
    name: ClassVar[str]
    format_patterns: ClassVar[List[re.Pattern]]
    
    @abstractmethod
    def parse(self, log_line: str) -> Optional[ParsedLogEntry]:
        """Parse a log line and return a structured log entry or None if cannot parse."""
        pass
    
    def validate(self, entry: ParsedLogEntry) -> bool:
        """
        Validate a parsed entry to ensure it meets minimum requirements for this format.
        Useful to verify structural validity in ambiguous formats.
        """
        # Base implementation performs basic validation
        # Subclasses should override for format-specific validation
        return (
            entry is not None and
            isinstance(entry.timestamp, datetime) and
            entry.message
        )
    
    def confidence(self, log_line: str, entry: ParsedLogEntry) -> float:
        """
        Return a confidence score between 0.0 and 1.0 indicating how confident
        this parser is that it correctly parsed the log line.
        Useful for resolver to choose best result among multiple valid parsers.
        """
        # Base implementation - subclasses should override for better heuristics
        if not self.can_parse(log_line) or not self.validate(entry):
            return 0.0
            
        # Simple heuristic: how much of the log was captured in structured fields
        # More structured data usually means better parsing
        structured_content = sum(len(str(v)) for v in entry.fields.values())
        total_content = len(log_line)
        
        if total_content == 0:
            return 0.0
            
        return min(structured_content / total_content, 1.0)
    
    @classmethod
    def can_parse(cls, log_line: str) -> bool:
        """Check if this parser can handle the given log line based on patterns."""
        return any(pattern.search(log_line) for pattern in cls.format_patterns)