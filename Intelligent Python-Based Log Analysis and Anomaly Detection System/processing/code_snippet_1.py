from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, List, Type, Optional, ClassVar
from datetime import datetime
import importlib.metadata
import re

@dataclass
class ParsedLogEntry:
    """Common representation of a parsed log entry across all formats."""
    timestamp: datetime
    level: str = "INFO"  # Default level
    message: str = ""
    source: str = ""
    fields: Dict[str, Any] = field(default_factory=dict)  # Format-specific fields
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the log entry to a dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "level": self.level,
            "message": self.message, 
            "source": self.source,
            **self.fields
        }

class LogParser(ABC):
    """Base interface for all log parsers."""
    
    # Class variables for plugin registration
    name: ClassVar[str]
    format_patterns: ClassVar[List[re.Pattern]]
    
    @abstractmethod
    def parse(self, log_line: str) -> Optional[ParsedLogEntry]:
        """Parse a log line and return a structured log entry or None if cannot parse."""
        pass
    
    @classmethod
    def can_parse(cls, log_line: str) -> bool:
        """Check if this parser can handle the given log line."""
        return any(pattern.match(log_line) for pattern in cls.format_patterns)

class ParserRegistry:
    """Registry for all available log parsers."""
    
    _parsers: Dict[str, Type[LogParser]] = {}
    
    @classmethod
    def register(cls, parser_class: Type[LogParser]) -> Type[LogParser]:
        """Register a parser class."""
        cls._parsers[parser_class.name] = parser_class
        return parser_class
    
    @classmethod
    def get_parser(cls, name: str) -> Optional[Type[LogParser]]:
        """Get a parser by name."""
        return cls._parsers.get(name)
    
    @classmethod
    def get_all_parsers(cls) -> Dict[str, Type[LogParser]]:
        """Get all registered parsers."""
        return cls._parsers.copy()
        
    @classmethod
    def discover_parsers(cls) -> None:
        """Discover and register parsers via entry points."""
        for entry_point in importlib.metadata.entry_points(group='log_parsers'):
            parser_class = entry_point.load()
            if issubclass(parser_class, LogParser):
                cls.register(parser_class)
    
    @classmethod
    def detect_parser(cls, log_line: str) -> Optional[Type[LogParser]]:
        """Detect the appropriate parser for a log line."""
        for parser_class in cls._parsers.values():
            if parser_class.can_parse(log_line):
                return parser_class
        return None

# Decorator for registering parsers
def register_parser(name: str, patterns: List[str]):
    """Decorator to register a parser with the registry."""
    def decorator(cls):
        cls.name = name
        cls.format_patterns = [re.compile(pattern) for pattern in patterns]
        return ParserRegistry.register(cls)
    return decorator