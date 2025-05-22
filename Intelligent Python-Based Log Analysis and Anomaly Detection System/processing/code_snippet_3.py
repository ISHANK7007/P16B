def process_logs(log_file, parser_name=None):
    # Discover all available parsers
    ParserRegistry.discover_parsers()
    
    # Choose a specific parser or use auto-detection
    parser_class = ParserRegistry.get_parser(parser_name) if parser_name else None
    
    with open(log_file, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
                
            # Auto-detect parser if not specified
            if not parser_class:
                parser_class = ParserRegistry.detect_parser(line)
                if not parser_class:
                    print(f"No parser found for line: {line[:80]}...")
                    continue
            
            # Create parser instance and parse the line
            parser = parser_class()
            entry = parser.parse(line)
            
            if entry:
                # Process the parsed entry
                print(f"Parsed entry: {entry.to_dict()}")
            else:
                print(f"Failed to parse line: {line[:80]}...")