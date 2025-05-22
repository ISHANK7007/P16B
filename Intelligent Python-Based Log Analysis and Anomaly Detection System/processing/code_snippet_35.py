from typing import Dict, List, Any, Optional, Callable, Type, Union, Set
from datetime import datetime, timezone
from enum import Enum, auto
import re
import json
from dataclasses import dataclass, field
import logging

class LogLevel(Enum):
    """Canonical log levels with numerical severity values."""
    TRACE = 0
    DEBUG = 1
    INFO = 2
    NOTICE = 3
    WARNING = 4
    ERROR = 5
    CRITICAL = 6
    ALERT = 7
    EMERGENCY = 8
    
    @classmethod
    def from_string(cls, level_str: str) -> 'LogLevel':
        """Convert a string representation to a LogLevel."""
        # Normalize the string
        normalized = level_str.upper().strip()
        
        # Direct mappings
        if normalized in ('TRACE', 'FINEST'):
            return cls.TRACE
        elif normalized in ('DEBUG', 'FINE', 'VERBOSE'):
            return cls.DEBUG
        elif normalized in ('INFO', 'INFORMATION', 'INFORMATIONAL'):
            return cls.INFO
        elif normalized in ('NOTICE'):
            return cls.NOTICE
        elif normalized in ('WARN', 'WARNING'):
            return cls.WARNING
        elif normalized in ('ERROR', 'ERR', 'SEVERE', 'EXCEPTION'):
            return cls.ERROR
        elif normalized in ('CRITICAL', 'CRIT', 'FATAL'):
            return cls.CRITICAL
        elif normalized in ('ALERT'):
            return cls.ALERT
        elif normalized in ('EMERGENCY', 'EMERG'):
            return cls.EMERGENCY
        
        # Numeric level mapping (approximate)
        try:
            level_int = int(normalized)
            # Syslog-style numeric levels
            if 0 <= level_int <= 8:
                return list(cls)[level_int]
            # Java/Log4j style numeric levels
            elif level_int <= 300:
                return cls.TRACE
            elif level_int <= 500:
                return cls.DEBUG
            elif level_int <= 800:
                return cls.INFO
            elif level_int <= 900:
                return cls.WARNING
            elif level_int <= 1000:
                return cls.ERROR
            else:
                return cls.CRITICAL
        except (ValueError, TypeError):
            pass
        
        # Default to INFO for unknown levels
        return cls.INFO

class FieldType(Enum):
    """Types of fields in normalized log entries."""
    STRING = auto()
    INTEGER = auto()
    FLOAT = auto()
    BOOLEAN = auto()
    TIMESTAMP = auto()
    OBJECT = auto()
    ARRAY = auto()
    IP_ADDRESS = auto()
    GEO_LOCATION = auto()
    DURATION = auto()
    LOG_LEVEL = auto()
    
    @classmethod
    def infer_type(cls, value: Any) -> 'FieldType':
        """Infer the field type from a value."""
        if isinstance(value, bool):
            return cls.BOOLEAN
        elif isinstance(value, int):
            return cls.INTEGER
        elif isinstance(value, float):
            return cls.FLOAT
        elif isinstance(value, (datetime, str)) and cls._looks_like_timestamp(value):
            return cls.TIMESTAMP
        elif isinstance(value, str):
            if cls._looks_like_ip(value):
                return cls.IP_ADDRESS
            else:
                return cls.STRING
        elif isinstance(value, dict):
            return cls.OBJECT
        elif isinstance(value, (list, tuple)):
            return cls.ARRAY
        else:
            return cls.STRING  # Default
    
    @staticmethod
    def _looks_like_timestamp(value: Any) -> bool:
        """Check if a value looks like a timestamp."""
        if isinstance(value, datetime):
            return True
            
        if not isinstance(value, str):
            return False
            
        # Check for ISO format
        if re.match(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}', value):
            return True
            
        # Check common date formats
        patterns = [
            r'^\d{4}-\d{2}-\d{2}',  # YYYY-MM-DD
            r'^\d{2}/\d{2}/\d{4}',  # MM/DD/YYYY
            r'^\d{2} [a-zA-Z]{3} \d{4}',  # DD MMM YYYY
        ]
        
        return any(re.match(pattern, value) for pattern in patterns)
    
    @staticmethod
    def _looks_like_ip(value: str) -> bool:
        """Check if a value looks like an IP address."""
        return re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', value) is not None

@dataclass
class FieldDefinition:
    """Definition of a field in the normalized log schema."""
    name: str  # Canonical field name
    type: FieldType  # Expected type
    description: str = ""  # Human-readable description
    required: bool = False  # Whether this field must be present
    aliases: List[str] = field(default_factory=list)  # Alternative names in source formats
    default_value: Any = None  # Default value if field is missing
    validation_pattern: Optional[str] = None  # Regex pattern for validation
    normalization_func: Optional[Callable[[Any], Any]] = None  # Function to normalize the value
    
    def validate(self, value: Any) -> bool:
        """Validate a value against this field definition."""
        # Check if field is required but missing
        if value is None:
            return not self.required
            
        # Check type compatibility (basic check)
        if not self._check_type_compatibility(value):
            return False
            
        # Check pattern if defined
        if self.validation_pattern and isinstance(value, str):
            if not re.match(self.validation_pattern, value):
                return False
                
        return True
    
    def normalize(self, value: Any) -> Any:
        """Normalize a value according to this field definition."""
        # Handle null values
        if value is None:
            return self.default_value
            
        # Apply custom normalization if provided
        if self.normalization_func:
            try:
                return self.normalization_func(value)
            except Exception as e:
                # Log the error but continue with default normalization
                logging.warning(f"Error in custom normalization for {self.name}: {e}")
        
        # Perform type-based normalization
        if self.type == FieldType.TIMESTAMP:
            return self._normalize_timestamp(value)
        elif self.type == FieldType.LOG_LEVEL:
            return self._normalize_log_level(value)
        elif self.type == FieldType.INTEGER:
            return self._normalize_integer(value)
        elif self.type == FieldType.FLOAT:
            return self._normalize_float(value)
        elif self.type == FieldType.BOOLEAN:
            return self._normalize_boolean(value)
        elif self.type == FieldType.STRING:
            return str(value) if value is not None else None
            
        # Default behavior: return as is
        return value
    
    def _check_type_compatibility(self, value: Any) -> bool:
        """Check if a value is compatible with the field type."""
        if self.type == FieldType.STRING:
            # Most values can be converted to strings
            return True
        elif self.type == FieldType.INTEGER:
            try:
                int(value) if value is not None else None
                return True
            except (ValueError, TypeError):
                return False
        elif self.type == FieldType.FLOAT:
            try:
                float(value) if value is not None else None
                return True
            except (ValueError, TypeError):
                return False
        elif self.type == FieldType.BOOLEAN:
            # Accept boolean-like values
            return isinstance(value, (bool, int)) or (
                isinstance(value, str) and value.lower() in ('true', 'false', '0', '1', 'yes', 'no')
            )
        elif self.type == FieldType.TIMESTAMP:
            # Accept datetime objects and timestamp strings
            return isinstance(value, datetime) or (
                isinstance(value, str) and FieldType._looks_like_timestamp(value)
            )
        elif self.type == FieldType.LOG_LEVEL:
            # Accept strings and integers
            return isinstance(value, (str, int))
        elif self.type == FieldType.IP_ADDRESS:
            return isinstance(value, str) and FieldType._looks_like_ip(value)
        elif self.type == FieldType.OBJECT:
            return isinstance(value, dict)
        elif self.type == FieldType.ARRAY:
            return isinstance(value, (list, tuple))
            
        # Default
        return True
    
    def _normalize_timestamp(self, value: Any) -> datetime:
        """Normalize a timestamp value to a datetime object."""
        if isinstance(value, datetime):
            # Ensure timezone is set
            if value.tzinfo is None:
                return value.replace(tzinfo=timezone.utc)
            return value
            
        if isinstance(value, (int, float)):
            # Assume Unix timestamp (seconds since epoch)
            try:
                if value > 1000000000000:  # Microseconds
                    return datetime.fromtimestamp(value / 1000000, timezone.utc)
                elif value > 1000000000:  # Milliseconds
                    return datetime.fromtimestamp(value / 1000, timezone.utc)
                else:  # Seconds
                    return datetime.fromtimestamp(value, timezone.utc)
            except (ValueError, OverflowError):
                # If conversion fails, return the default value
                return self.default_value
            
        if isinstance(value, str):
            # Try multiple formats
            formats = [
                # ISO formats
                '%Y-%m-%dT%H:%M:%S.%fZ',
                '%Y-%m-%dT%H:%M:%S%z',
                '%Y-%m-%dT%H:%M:%S.%f%z',
                '%Y-%m-%dT%H:%M:%S',
                '%Y-%m-%dT%H:%M:%S.%f',
                
                # Common log formats
                '%d/%b/%Y:%H:%M:%S %z',  # Apache
                '%Y-%m-%d %H:%M:%S,%f',  # Log4j
                '%Y-%m-%d %H:%M:%S.%f',  # Python
                '%b %d %H:%M:%S',        # Syslog
                '%Y/%m/%d %H:%M:%S',     # Custom
                
                # Other common formats
                '%Y-%m-%d',
                '%m/%d/%Y',
                '%d/%m/%Y',
            ]
            
            # Try each format
            for fmt in formats:
                try:
                    dt = datetime.strptime(value, fmt)
                    # Add timezone if missing
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    return dt
                except ValueError:
                    continue
        
        # If all parsing attempts fail, return default
        return self.default_value
    
    def _normalize_log_level(self, value: Any) -> str:
        """Normalize a log level value to a canonical string."""
        try:
            if isinstance(value, str):
                level = LogLevel.from_string(value)
            elif isinstance(value, int):
                # Try to map numeric level
                if 0 <= value <= 8:
                    level = list(LogLevel)[value]
                else:
                    # Approximate mapping for other numeric scales
                    normalized = min(max(0, value), 1000) / 1000.0  # Normalize to 0-1
                    index = min(int(normalized * len(LogLevel)), len(LogLevel) - 1)
                    level = list(LogLevel)[index]
            else:
                level = LogLevel.INFO  # Default
                
            return level.name
        except:
            return "INFO"  # Default to INFO for any errors
    
    def _normalize_integer(self, value: Any) -> Optional[int]:
        """Normalize a value to an integer."""
        if value is None:
            return self.default_value
            
        try:
            if isinstance(value, bool):
                return 1 if value else 0
            return int(value)
        except (ValueError, TypeError):
            return self.default_value
    
    def _normalize_float(self, value: Any) -> Optional[float]:
        """Normalize a value to a float."""
        if value is None:
            return self.default_value
            
        try:
            return float(value)
        except (ValueError, TypeError):
            return self.default_value
    
    def _normalize_boolean(self, value: Any) -> Optional[bool]:
        """Normalize a value to a boolean."""
        if value is None:
            return self.default_value
            
        if isinstance(value, bool):
            return value
            
        if isinstance(value, (int, float)):
            return value != 0
            
        if isinstance(value, str):
            return value.lower() in ('true', 'yes', 'y', '1', 'on')
            
        return bool(value)

class ParsedLogSchema:
    """Schema definition for normalized log entries."""
    
    def __init__(self, name: str, version: str = "1.0.0"):
        self.name = name
        self.version = version
        self.fields: Dict[str, FieldDefinition] = {}
        self.alias_map: Dict[str, str] = {}  # Maps aliases to canonical names
        
        # Initialize with common fields
        self._initialize_common_fields()
    
    def _initialize_common_fields(self) -> None:
        """Initialize schema with common log fields."""
        # Timestamp field
        self.add_field(FieldDefinition(
            name="timestamp",
            type=FieldType.TIMESTAMP,
            description="When the log event occurred",
            required=True,
            aliases=["time", "@timestamp", "eventTime", "date", "event_time"],
            default_value=datetime.now(timezone.utc)
        ))
        
        # Log level
        self.add_field(FieldDefinition(
            name="level",
            type=FieldType.LOG_LEVEL,
            description="Severity level of the log entry",
            required=True,
            aliases=["severity", "loglevel", "log_level", "priority", "syslog_level"],
            default_value="INFO"
        ))
        
        # Log message
        self.add_field(FieldDefinition(
            name="message",
            type=FieldType.STRING,
            description="Main log message content",
            required=True,
            aliases=["msg", "log", "text", "description", "content"],
            default_value=""
        ))
        
        # Source information
        self.add_field(FieldDefinition(
            name="source",
            type=FieldType.STRING,
            description="Source of the log (application, service, etc.)",
            required=False,
            aliases=["logger", "source_name", "application", "app", "service"],
            default_value=None
        ))
        
        # Host information
        self.add_field(FieldDefinition(
            name="host",
            type=FieldType.STRING,
            description="Host that generated the log",
            required=False,
            aliases=["hostname", "machine", "node", "server"],
            default_value=None
        ))
        
        # Process ID
        self.add_field(FieldDefinition(
            name="pid",
            type=FieldType.INTEGER,
            description="Process ID that generated the log",
            required=False,
            aliases=["process_id", "process"],
            default_value=None
        ))
    
    def add_field(self, field_def: FieldDefinition) -> None:
        """
        Add a field definition to the schema.
        
        Args:
            field_def: The field definition to add
        """
        self.fields[field_def.name] = field_def
        
        # Update alias map
        for alias in field_def.aliases:
            self.alias_map[alias] = field_def.name
    
    def get_field(self, field_name: str) -> Optional[FieldDefinition]:
        """
        Get a field definition by name or alias.
        
        Args:
            field_name: Field name or alias
            
        Returns:
            The field definition or None if not found
        """
        # Check if it's a canonical name
        if field_name in self.fields:
            return self.fields[field_name]
            
        # Check if it's an alias
        canonical_name = self.alias_map.get(field_name)
        if canonical_name:
            return self.fields[canonical_name]
            
        return None
    
    def get_canonical_name(self, field_name: str) -> str:
        """
        Get the canonical field name for a given field name or alias.
        
        Args:
            field_name: Field name or alias
            
        Returns:
            The canonical field name, or the original name if not mapped
        """
        if field_name in self.fields:
            return field_name
            
        return self.alias_map.get(field_name, field_name)
    
    def normalize_entry(self, log_entry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize a log entry according to the schema.
        
        Args:
            log_entry: The log entry to normalize
            
        Returns:
            A normalized log entry with canonical field names and normalized values
        """
        normalized = {}
        
        # Process known fields first
        for field_name, field_def in self.fields.items():
            # Look for the field by canonical name or aliases
            value = None
            
            # Try canonical name first
            if field_name in log_entry:
                value = log_entry[field_name]
            else:
                # Try aliases
                for alias in field_def.aliases:
                    if alias in log_entry:
                        value = log_entry[alias]
                        break
            
            # Normalize the value
            normalized[field_name] = field_def.normalize(value)
        
        # Add any additional fields not in the schema
        for key, value in log_entry.items():
            canonical_name = self.get_canonical_name(key)
            
            # Skip fields we've already processed
            if canonical_name in normalized:
                continue
                
            # Add the field with its original name (we could use canonical_name instead)
            normalized[key] = value
        
        return normalized
    
    def validate_entry(self, log_entry: Dict[str, Any]) -> bool:
        """
        Validate a log entry against the schema.
        
        Args:
            log_entry: The log entry to validate
            
        Returns:
            True if the entry is valid, False otherwise
        """
        # Check required fields
        for field_name, field_def in self.fields.items():
            if field_def.required:
                # Try to find the field by canonical name or aliases
                found = False
                if field_name in log_entry:
                    found = True
                    value = log_entry[field_name]
                else:
                    # Try aliases
                    for alias in field_def.aliases:
                        if alias in log_entry:
                            found = True
                            value = log_entry[alias]
                            break
                
                # If required field is missing, validation fails
                if not found:
                    return False
                
                # Validate the value
                if not field_def.validate(value):
                    return False
        
        return True