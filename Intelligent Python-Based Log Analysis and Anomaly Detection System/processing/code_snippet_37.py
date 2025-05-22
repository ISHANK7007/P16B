class LogNormalizationManager:
    """Manager for log field normalization across different formats."""
    
    def __init__(self):
        # Create the base schema
        self.schema = ParsedLogSchema(name="canonical_log")
        
        # Create the registry mapper
        self.registry_mapper = ParserRegistryMapper(self.schema)
        
        # Initialize format-specific mappers
        self._init_format_mappers()
    
    def _init_format_mappers(self) -> None:
        """Initialize format-specific mappers."""
        # Create mappers for common formats
        syslog_mapper = SyslogMapper(self.schema)
        apache_mapper = ApacheAccessLogMapper(self.schema)
        json_mapper = JsonLogMapper(self.schema)
        cloudwatch_mapper = CloudWatchLogMapper(self.schema)
        
        # Register mappers with the registry
        self.registry_mapper.register_mapper("syslog", syslog_mapper)
        self.registry_mapper.register_mapper("apache_access", apache_mapper)
        self.registry_mapper.register_mapper("json", json_mapper)
        self.registry_mapper.register_mapper("cloudwatch", cloudwatch_mapper)
    
    def register_format_mapper(self, parser_name: str, mapper: FormatSpecificMapper) -> None:
        """Register a custom format mapper."""
        self.registry_mapper.register_mapper(parser_name, mapper)
    
    def normalize(self, log_entry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize a parsed log entry using the appropriate mapper.
        
        Args:
            log_entry: The parsed log entry
            
        Returns:
            A normalized log entry with canonical field names and values
        """
        return self.registry_mapper.map_and_normalize(log_entry)
    
    def extend_schema(self, field_def: FieldDefinition) -> None:
        """
        Extend the schema with a new field definition.
        
        Args:
            field_def: The field definition to add
        """
        self.schema.add_field(field_def)