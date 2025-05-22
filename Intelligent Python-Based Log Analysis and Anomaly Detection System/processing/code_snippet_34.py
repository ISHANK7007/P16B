async def process_mixed_log_directory():
    # Initialize the pipeline
    pipeline = AdaptiveLogProcessingPipeline()
    
    # Create an in-memory database for storing parsed entries
    import sqlite3
    conn = sqlite3.connect(':memory:')
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE logs (
        timestamp TEXT,
        level TEXT,
        source TEXT,
        message TEXT,
        parser TEXT,
        format TEXT,
        data TEXT
    )
    ''')
    
    # Handler to store entries in the database
    async def db_handler(entry: ParsedLogEntry):
        # Serialize entry data
        import json
        entry_data = json.dumps(entry.to_dict())
        
        # Insert into database
        cursor.execute(
            'INSERT INTO logs VALUES (?, ?, ?, ?, ?, ?, ?)',
            (
                entry.timestamp.isoformat(),
                entry.level,
                entry.source,
                entry.message,
                entry.parser_metadata.get('parser_name', 'unknown'),
                entry.parser_metadata.get('format', 'unknown'),
                entry_data
            )
        )
        conn.commit()
    
    # Get all log files in a directory
    log_dir = '/var/log'
    log_files = [f for f in os.listdir(log_dir) if f.endswith('.log')]
    
    # Create sources for each file
    sources = [
        LogSource(
            source_id=f"log-{i}",
            source_type="file",
            path=os.path.join(log_dir, filename)
        )
        for i, filename in enumerate(log_files)
    ]
    
    # Process all sources
    stats = await pipeline.process_multiple_sources(sources, db_handler)
    
    # Print results
    print(f"Processed {stats['total_lines_processed']} lines from {stats['sources_processed']} sources")
    print(f"Successfully parsed: {stats['total_lines_parsed']} lines")
    print(f"Parse failures: {stats['total_parse_failures']} lines")
    
    # Query database to see distribution of log formats
    cursor.execute('''
    SELECT parser, COUNT(*) FROM logs GROUP BY parser ORDER BY COUNT(*) DESC
    ''')
    for parser, count in cursor.fetchall():
        print(f"Parser {parser}: {count} entries")

# Run the function
asyncio.run(process_mixed_log_directory())