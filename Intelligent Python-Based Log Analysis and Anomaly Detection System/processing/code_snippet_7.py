@register_parser(
    name="syslog",
    patterns=[
        r'<\d+>[\w\s:]+ [\w\.-]+ \w+(\[\d+\])?:',  # Standard syslog
        r'[\w\s:]+ [\w\.-]+ \w+\[\d+\]:',          # BSD-style syslog
    ]
)
class SyslogParser(LogParser):
    """Parser for syslog format logs."""
    
    def parse(self, log_line: str) -> Optional[ParsedLogEntry]:
        # Multiple pattern matching for different syslog variations
        # Standard format: <facility.priority>timestamp hostname process[pid]: message
        std_pattern = re.compile(
            r'<(\d+)>([A-Za-z]{3}\s+\d+ \d+:\d+:\d+) ([^ ]+) ([^\[:]+)(?:\[(\d+)\])?: (.*)'
        )
        
        # BSD format: timestamp hostname process[pid]: message
        bsd_pattern = re.compile(
            r'([A-Za-z]{3}\s+\d+ \d+:\d+:\d+) ([^ ]+) ([^\[:]+)(?:\[(\d+)\])?: (.*)'
        )
        
        # Try standard format first
        match = std_pattern.match(log_line)
        if match:
            priority, timestamp_str, hostname, process, pid, message = match.groups()
            # Convert priority to level (simplified)
            level = self._priority_to_level(int(priority))
        else:
            # Try BSD format
            match = bsd_pattern.match(log_line)
            if not match:
                return None
                
            timestamp_str, hostname, process, pid, message = match.groups()
            level = "INFO"  # Default level for BSD format
        
        try:
            # Parse timestamp (may need more robust handling)
            current_year = datetime.now().year
            timestamp = datetime.strptime(f"{current_year} {timestamp_str}", "%Y %b %d %H:%M:%S")
            
            return ParsedLogEntry(
                timestamp=timestamp,
                level=level,
                message=message,
                source=f"{hostname}/{process}",
                fields={
                    "process": process,
                    "pid": int(pid) if pid else None,
                    "hostname": hostname
                }
            )
        except Exception:
            return None
    
    def _priority_to_level(self, priority: int) -> str:
        """Convert syslog priority to log level."""
        # Extract severity from priority (lower 3 bits)
        severity = priority & 0x7
        
        # Map severity to level
        severity_map = {
            0: "EMERGENCY",  # System is unusable
            1: "ALERT",      # Action must be taken immediately
            2: "CRITICAL",   # Critical conditions
            3: "ERROR",      # Error conditions
            4: "WARNING",    # Warning conditions
            5: "NOTICE",     # Normal but significant condition
            6: "INFO",       # Informational
            7: "DEBUG"       # Debug-level messages
        }
        
        return severity_map.get(severity, "INFO")
    
    def confidence(self, log_line: str, entry: Optional[ParsedLogEntry]) -> float:
        """Specialized confidence estimation for syslog."""
        if not entry:
            return 0.0
            
        base_confidence = super().confidence(log_line, entry)
        
        # Add confidence if we have expected syslog fields
        if entry.fields.get("process") and entry.fields.get("hostname"):
            base_confidence += 0.2
            
        # Syslog messages typically have a clear process identifier
        if entry.fields.get("pid"):
            base_confidence += 0.1
            
        return min(base_confidence, 1.0)

@register_parser(
    name="custom_app",
    patterns=[
        r'\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\] \[\w+\]',  # [YYYY-MM-DD HH:MM:SS] [LEVEL]
    ]
)
class CustomAppLogParser(LogParser):
    """Parser for a custom application log format."""
    
    def parse(self, log_line: str) -> Optional[ParsedLogEntry]:
        # Custom format: [YYYY-MM-DD HH:MM:SS] [LEVEL] [COMPONENT] - Message
        pattern = re.compile(
            r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\] \[([^\]]+)\](?: \[([^\]]+)\])? - (.*)'
        )
        
        match = pattern.match(log_line)
        if not match:
            return None
            
        timestamp_str, level, component, message = match.groups()
        
        try:
            timestamp = datetime.fromisoformat(timestamp_str)
            
            return ParsedLogEntry(
                timestamp=timestamp,
                level=level.upper(),
                message=message,
                source=component or "custom_app",
                fields={
                    "component": component,
                    "raw_level": level
                }
            )
        except Exception:
            return None
    
    def validate(self, entry: ParsedLogEntry) -> bool:
        """Custom validation for app logs."""
        base_valid = super().validate(entry)
        if not base_valid:
            return False
            
        # Custom app logs should have a level in a recognized format
        valid_levels = {"DEBUG", "INFO", "WARN", "WARNING", "ERROR", "FATAL", "CRITICAL"}
        return entry.level.upper() in valid_levels