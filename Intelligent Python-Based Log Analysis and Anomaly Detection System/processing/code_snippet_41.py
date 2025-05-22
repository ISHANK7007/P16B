# Create the normalization manager
normalization_manager = LogNormalizationManager()

# Create a schema extender to add custom fields
schema_extender = SchemaExtender(normalization_manager.schema)

# Add custom field extraction - e.g., extract correlation ID from message
schema_extender.add_custom_extraction(
    source_field="message",
    target_field="correlation_id",
    extraction_pattern=r'correlationId[=:]\s*([a-zA-Z0-9-]+)',
    field_type=FieldType.STRING,
    description="Correlation ID for request tracing"
)

# Add custom field that combines values
schema_extender.add_compound_field(
    target_field="full_source",
    source_fields=["source", "host", "pid"],
    aggregation_func=lambda values: "/".join(str(v) for v in values if v),
    field_type=FieldType.STRING,
    description="Full source identifier"
)

# Create a normalizing log ingestion controller
controller = NormalizingLogIngestionController(
    parser_resolver=optimized_resolver,
    normalization_manager=normalization_manager
)

# Process logs with normalization
async def process_logs():
    source = LogSource(
        source_id="app-logs",
        source_type="file",
        path="/var/log/application.log"
    )
    
    async def handle_entry(entry: ParsedLogEntry):
        # All entries will have normalized fields
        print(f"[{entry.timestamp}] {entry.level}: {entry.message}")
        print(f"Source: {entry.source}")
        if "correlation_id" in entry.fields:
            print(f"Correlation ID: {entry.fields['correlation_id']}")
    
    await controller.ingest_log_source(source, asyncio.Queue())

# Run the log processor
asyncio.run(process_logs())