class SchemaExtender:
    """Utility for extending the log schema with custom fields."""
    
    def __init__(self, schema: ParsedLogSchema):
        self.schema = schema
    
    def add_custom_normalized_field(self,
                                 name: str,
                                 field_type: FieldType,
                                 normalization_func: Callable[[Any], Any],
                                 description: str = "",
                                 aliases: List[str] = None) -> None:
        """
        Add a custom field with a specialized normalization function.
        
        Args:
            name: Canonical field name
            field_type: Field type
            normalization_func: Function to normalize the field value
            description: Field description
            aliases: Alternative names for this field
        """
        field_def = FieldDefinition(
            name=name,
            type=field_type,
            description=description,
            required=False,
            aliases=aliases or [],
            default_value=None,
            normalization_func=normalization_func
        )
        
        self.schema.add_field(field_def)
    
    def add_custom_extraction(self,
                           source_field: str,
                           target_field: str,
                           extraction_pattern: str,
                           field_type: FieldType = FieldType.STRING,
                           description: str = "") -> None:
        """
        Add a field that will be extracted from another field using regex.
        
        Args:
            source_field: Field to extract from
            target_field: Field to store the extracted value
            extraction_pattern: Regex pattern with a capture group
            field_type: Target field type
            description: Target field description
        """
        pattern = re.compile(extraction_pattern)
        
        def extract_value(source_value: Any) -> Any:
            if not isinstance(source_value, str):
                return None
                
            match = pattern.search(source_value)
            if not match:
                return None
                
            return match.group(1) if match.groups() else match.group(0)
        
        self.add_custom_normalized_field(
            name=target_field,
            field_type=field_type,
            normalization_func=extract_value,
            description=description,
            aliases=[]
        )
    
    def add_compound_field(self,
                        target_field: str,
                        source_fields: List[str],
                        aggregation_func: Callable[[List[Any]], Any],
                        field_type: FieldType = FieldType.STRING,
                        description: str = "") -> None:
        """
        Add a field that combines values from multiple source fields.
        
        Args:
            target_field: Field to store the combined value
            source_fields: Fields to combine
            aggregation_func: Function to combine the source values
            field_type: Target field type
            description: Target field description
        """
        def combine_values(log_entry: Dict[str, Any]) -> Any:
            # This function will be called with the entire log entry
            values = []
            for field in source_fields:
                # Try canonical name and aliases
                field_def = self.schema.get_field(field)
                if field_def:
                    # Look for the field by canonical name or aliases
                    value = None
                    
                    # Try canonical name
                    if field_def.name in log_entry:
                        value = log_entry[field_def.name]
                    else:
                        # Try aliases
                        for alias in field_def.aliases:
                            if alias in log_entry:
                                value = log_entry[alias]
                                break
                    
                    values.append(value)
                else:
                    # Just look for the exact field name
                    values.append(log_entry.get(field))
            
            return aggregation_func(values)
        
        # Add a special normalization function that requires the whole entry
        self.schema.add_field(FieldDefinition(
            name=target_field,
            type=field_type,
            description=description,
            required=False,
            aliases=[],
            default_value=None,
            # This is a special case - the normalization function won't be called
            # directly by the schema normalizer, but by a custom mapper
            normalization_func=None
        ))