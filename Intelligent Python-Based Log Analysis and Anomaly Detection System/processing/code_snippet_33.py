async def main():
    # Initialize the pipeline
    pipeline = AdaptiveLogProcessingPipeline()
    
    # Define a handler for parsed entries
    async def entry_handler(entry: ParsedLogEntry):
        # Process the parsed entry (e.g., store in database)
        print(f"[{entry.timestamp}] {entry.level}: {entry.message}")
    
    # Define a log source
    source = LogSource(
        source_id="app-logs-1",
        source_type="file",
        path="/var/log/application.log"
    )
    
    # Process the source
    stats = await pipeline.process_log_source(source, entry_handler)
    print(f"Processed {stats['lines_processed']} lines")

# Run the main function
asyncio.run(main())