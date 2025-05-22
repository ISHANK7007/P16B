from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Set, Tuple
from enum import Enum
from datetime import datetime
import json

class ParserResult(Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    REJECTED = "rejected"
    ERROR = "error"
    SKIPPED = "skipped"

@dataclass
class ParserAttempt:
    """Record of a single parser's attempt to parse a log line."""
    parser_name: str
    result: ParserResult
    confidence: float
    duration_ms: float
    error_message: Optional[str] = None
    extracted_fields: Set[str] = field(default_factory=set)
    rejected_reason: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "parser": self.parser_name,
            "result": self.result.value,
            "confidence": round(self.confidence, 4),
            "duration_ms": round(self.duration_ms, 2),
            "fields_extracted": sorted(list(self.extracted_fields))
        }
        
        if self.error_message:
            result["error"] = self.error_message
            
        if self.rejected_reason:
            result["rejected_reason"] = self.rejected_reason
            
        return result

@dataclass
class ParserTrace:
    """Complete trace of all parser attempts for a single log line."""
    trace_id: str
    raw_log: str
    timestamp: datetime
    attempts: List[ParserAttempt] = field(default_factory=list)
    selected_parser: Optional[str] = None
    parsing_time_ms: float = 0.0
    conflict_detected: bool = False
    conflict_resolution: Optional[str] = None
    
    def add_attempt(self, attempt: ParserAttempt) -> None:
        """Add a parser attempt to the trace."""
        self.attempts.append(attempt)
        
    def get_successful_attempts(self) -> List[ParserAttempt]:
        """Get all successful parsing attempts."""
        return [a for a in self.attempts if a.result == ParserResult.SUCCESS]
    
    def has_conflicts(self) -> bool:
        """Check if multiple parsers claim to successfully parse the log."""
        successful = self.get_successful_attempts()
        return len(successful) > 1
    
    def get_field_conflicts(self) -> Dict[str, List[Tuple[str, Any]]]:
        """
        Identify specific fields with conflicting values across parsers.
        Returns a dictionary mapping field names to a list of (parser_name, value) tuples.
        """
        # This would require access to the actual parsed entries, which we could add
        # but for illustration we'll return a placeholder
        return {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the trace to a dictionary for serialization."""
        return {
            "trace_id": self.trace_id,
            "timestamp": self.timestamp.isoformat(),
            "raw_log": self.raw_log[:1000] if len(self.raw_log) > 1000 else self.raw_log,
            "selected_parser": self.selected_parser,
            "total_time_ms": round(self.parsing_time_ms, 2),
            "attempts": [a.to_dict() for a in self.attempts],
            "conflict_detected": self.conflict_detected,
            "conflict_resolution": self.conflict_resolution if self.conflict_detected else None
        }
    
    def __str__(self) -> str:
        """String representation of the trace."""
        return json.dumps(self.to_dict(), indent=2)