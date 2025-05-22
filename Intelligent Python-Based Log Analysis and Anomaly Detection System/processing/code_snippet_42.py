# Create a custom mapper for a proprietary log format
class ProprietaryLogMapper(FormatSpecificMapper):
    """Mapper for a proprietary log format."""
    
    def _setup_mappings(self) -> None:
        # Add custom fields
        self.schema.add_field(FieldDefinition(
            name="customer_id",
            type=FieldType.STRING,
            description="Customer identifier",
            required=False,
            aliases=["cust_id", "customer", "cid"],
            default_value=None
        ))
    
    def preprocess(self, log_entry: Dict[str, Any]) -> Dict[str, Any]:
        entry = log_entry.copy()
        
        # Handle proprietary format quirks
        if "raw_log" in entry and isinstance(entry["raw_log"], str):
            # Extract customer ID using regex
            cid_match = re.search(r'CID:([A-Z0-9]+)', entry["raw_log"])
            if cid_match:
                entry["customer_id"] = cid_match.group(1)
        
        # Transform weird timestamp format
        if "event_time" in entry and isinstance(entry["event_time"], str):
            # Example: "20210716-143022" -> "2021-07-16T14:30:22"
            weird_ts = entry["event_time"]
            if re.match(r'^\d{8}-\d{6}$', weird_ts):
                fixed_ts = f"{weird_ts[:4]}-{weird_ts[4:6]}-{weird_ts[6:8]}T{weird_ts[9:11]}:{weird_ts[11:13]}:{weird_ts[13:15]}"
                entry["timestamp"] = fixed_ts
        
        return entry

# Register the custom mapper
normalization_manager.register_format_mapper("proprietary_format", 
                                            ProprietaryLogMapper(normalization_manager.schema))