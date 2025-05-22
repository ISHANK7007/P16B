class FormatSpecificMapper:
    """Base class for format-specific field mapping and normalization."""
    
    def __init__(self, schema: ParsedLogSchema):
        self.schema = schema
        self._setup_mappings()
    
    def _setup_mappings(self) -> None:
        """Set up format-specific mappings. Override in subclasses."""
        pass
    
    def preprocess(self, log_entry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Preprocess a log entry by applying format-specific transformations.
        Override in subclasses.
        """
        return log_entry
    
    def map_and_normalize(self, log_entry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map and normalize a log entry according to the schema.
        
        Args:
            log_entry: The log entry to normalize
            
        Returns:
            A normalized log entry
        """
        # Apply preprocessor
        preprocessed = self.preprocess(log_entry)
        
        # Apply schema normalization
        return self.schema.normalize_entry(preprocessed)

class SyslogMapper(FormatSpecificMapper):
    """Mapper for syslog format."""
    
    def _setup_mappings(self) -> None:
        # Add syslog-specific field definitions if needed
        self.schema.add_field(FieldDefinition(
            name="facility",
            type=FieldType.STRING,
            description="Syslog facility",
            required=False,
            aliases=["syslog_facility"],
            default_value=None
        ))
        
        self.schema.add_field(FieldDefinition(
            name="priority",
            type=FieldType.INTEGER,
            description="Syslog priority (facility * 8 + severity)",
            required=False,
            aliases=["syslog_priority", "pri"],
            default_value=None
        ))
    
    def preprocess(self, log_entry: Dict[str, Any]) -> Dict[str, Any]:
        entry = log_entry.copy()
        
        # Extract fields from raw message if needed
        if "raw_message" in entry and isinstance(entry["raw_message"], str):
            raw = entry["raw_message"]
            
            # Extract priority if present at the beginning: <N>
            priority_match = re.match(r'<(\d+)>(.*)', raw)
            if priority_match:
                pri = int(priority_match.group(1))
                entry["priority"] = pri
                
                # Calculate facility and severity
                facility = pri // 8
                severity = pri % 8
                
                entry["facility"] = facility
                if "level" not in entry:
                    # Map syslog severity (0-7) to log level
                    syslog_levels = ["EMERGENCY", "ALERT", "CRITICAL", "ERROR", 
                                   "WARNING", "NOTICE", "INFO", "DEBUG"]
                    entry["level"] = syslog_levels[severity]
                
                # Update the message without the priority prefix
                if "message" not in entry:
                    entry["message"] = priority_match.group(2)
        
        # Handle timestamp format conversion
        if "timestamp" in entry and isinstance(entry["timestamp"], str):
            # Look for common syslog timestamp formats
            # e.g., "Jan 23 14:59:32" or "2021 Jan 23 14:59:32"
            ts = entry["timestamp"]
            
            # If year is missing, add current year
            if re.match(r'^[A-Za-z]{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}', ts):
                current_year = datetime.now().year
                ts = f"{current_year} {ts}"
                entry["timestamp"] = ts
        
        return entry

class ApacheAccessLogMapper(FormatSpecificMapper):
    """Mapper for Apache access logs."""
    
    def _setup_mappings(self) -> None:
        # Add Apache-specific field definitions
        self.schema.add_field(FieldDefinition(
            name="client_ip",
            type=FieldType.IP_ADDRESS,
            description="Client IP address",
            required=False,
            aliases=["ip", "clientip", "remote_addr"],
            default_value=None
        ))
        
        self.schema.add_field(FieldDefinition(
            name="method",
            type=FieldType.STRING,
            description="HTTP method",
            required=False,
            aliases=["http_method", "request_method"],
            default_value=None
        ))
        
        self.schema.add_field(FieldDefinition(
            name="path",
            type=FieldType.STRING,
            description="Request path",
            required=False,
            aliases=["request_path", "uri", "url"],
            default_value=None
        ))
        
        self.schema.add_field(FieldDefinition(
            name="status",
            type=FieldType.INTEGER,
            description="HTTP status code",
            required=False,
            aliases=["status_code", "http_status", "response_code"],
            default_value=None
        ))
        
        self.schema.add_field(FieldDefinition(
            name="size",
            type=FieldType.INTEGER,
            description="Response size in bytes",
            required=False,
            aliases=["bytes", "response_size", "content_length"],
            default_value=None
        ))
        
        self.schema.add_field(FieldDefinition(
            name="user_agent",
            type=FieldType.STRING,
            description="User agent string",
            required=False,
            aliases=["agent", "browser", "http_user_agent"],
            default_value=None
        ))
        
        self.schema.add_field(FieldDefinition(
            name="referer",
            type=FieldType.STRING,
            description="HTTP referer",
            required=False,
            aliases=["referrer", "http_referer"],
            default_value=None
        ))
    
    def preprocess(self, log_entry: Dict[str, Any]) -> Dict[str, Any]:
        entry = log_entry.copy()
        
        # Extract components from request field if present
        if "request" in entry and isinstance(entry["request"], str):
            parts = entry["request"].split()
            if len(parts) >= 2:
                entry["method"] = parts[0]
                entry["path"] = parts[1]
        
        # Compose a meaningful message if not present
        if "message" not in entry and "path" in entry and "status" in entry:
            status = entry["status"]
            path = entry["path"]
            method = entry.get("method", "")
            
            entry["message"] = f"{method} {path} {status}"
        
        # Set a default level based on status code
        if "level" not in entry and "status" in entry:
            status = int(entry["status"])
            if status < 400:
                entry["level"] = "INFO"
            elif status < 500:
                entry["level"] = "WARNING"
            else:
                entry["level"] = "ERROR"
        
        # Set source if not present
        if "source" not in entry:
            entry["source"] = "apache_access"
        
        return entry

class JsonLogMapper(FormatSpecificMapper):
    """Mapper for JSON log formats."""
    
    def _setup_mappings(self) -> None:
        # JSON logs can have nested structures
        self.schema.add_field(FieldDefinition(
            name="context",
            type=FieldType.OBJECT,
            description="Contextual information about the log",
            required=False,
            aliases=["ctx", "contextMap", "log_context"],
            default_value=None
        ))
        
        self.schema.add_field(FieldDefinition(
            name="error",
            type=FieldType.OBJECT,
            description="Error details",
            required=False,
            aliases=["exception", "err", "error_details"],
            default_value=None
        ))
    
    def preprocess(self, log_entry: Dict[str, Any]) -> Dict[str, Any]:
        entry = log_entry.copy()
        
        # Extract fields from nested structures
        if "error" in entry and isinstance(entry["error"], dict):
            error = entry["error"]
            
            # Extract error message if not already in main message
            if "message" not in entry and "message" in error:
                entry["message"] = error["message"]
                
            # Extract stack trace if available
            if "stack" in error:
                entry["stack_trace"] = error["stack"]
        
        # Handle event-style logs (e.g., from ELK)
        if "@timestamp" in entry and "timestamp" not in entry:
            entry["timestamp"] = entry["@timestamp"]
        
        # Extract message from alternate locations
        if "message" not in entry:
            for field in ["msg", "log", "text", "content"]:
                if field in entry:
                    entry["message"] = entry[field]
                    break
        
        return entry

class CloudWatchLogMapper(FormatSpecificMapper):
    """Mapper for AWS CloudWatch Logs."""
    
    def _setup_mappings(self) -> None:
        self.schema.add_field(FieldDefinition(
            name="log_group",
            type=FieldType.STRING,
            description="CloudWatch log group",
            required=False,
            aliases=["logGroup", "group"],
            default_value=None
        ))
        
        self.schema.add_field(FieldDefinition(
            name="log_stream",
            type=FieldType.STRING,
            description="CloudWatch log stream",
            required=False,
            aliases=["logStream", "stream"],
            default_value=None
        ))
        
        self.schema.add_field(FieldDefinition(
            name="aws_region",
            type=FieldType.STRING,
            description="AWS region",
            required=False,
            aliases=["region", "awsRegion"],
            default_value=None
        ))
    
    def preprocess(self, log_entry: Dict[str, Any]) -> Dict[str, Any]:
        entry = log_entry.copy()
        
        # Unpack lambda or container logs if needed
        if "message" in entry and isinstance(entry["message"], str):
            try:
                # Check if message is JSON
                message_data = json.loads(entry["message"])
                if isinstance(message_data, dict):
                    # Flatten main fields from the nested message
                    for key in ["timestamp", "level", "message"]:
                        if key in message_data and key not in entry:
                            entry[key] = message_data[key]
                            
                    # Keep the original JSON as a nested field
                    entry["log_event"] = message_data
            except (json.JSONDecodeError, TypeError):
                # Not JSON, keep as is
                pass
        
        # Set source from log group if available
        if "source" not in entry and "log_group" in entry:
            # Extract app name from log group
            # e.g., /aws/lambda/my-function -> lambda/my-function
            log_group = entry["log_group"]
            source = log_group.split('/')[-2:]
            entry["source"] = '/'.join(source)
            
        return entry

class ParserRegistryMapper(FormatSpecificMapper):
    """Special mapper that selects the appropriate mapper based on parser."""
    
    def __init__(self, schema: ParsedLogSchema):
        super().__init__(schema)
        self.format_mappers = {}
    
    def register_mapper(self, parser_name: str, mapper: FormatSpecificMapper) -> None:
        """Register a mapper for a specific parser."""
        self.format_mappers[parser_name] = mapper
    
    def get_mapper(self, parser_name: str) -> FormatSpecificMapper:
        """Get the appropriate mapper for a parser."""
        return self.format_mappers.get(parser_name, self)
    
    def map_and_normalize(self, log_entry: Dict[str, Any]) -> Dict[str, Any]:
        """Map and normalize using the appropriate format-specific mapper."""
        # Check if we have parser information
        parser_name = None
        if "_parser" in log_entry and isinstance(log_entry["_parser"], dict):
            parser_name = log_entry["_parser"].get("name")
        
        if parser_name and parser_name in self.format_mappers:
            # Use the specific mapper
            return self.format_mappers[parser_name].map_and_normalize(log_entry)
        
        # Fall back to generic normalization
        return self.schema.normalize_entry(log_entry)