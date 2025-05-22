def process_mixed_log_file(filename: str, resolver: ParserResolver):
    """Process a log file with mixed formats."""
    unparseable_lines = []
    stats = {"total": 0, "parsed": 0, "parsers": {}}
    
    with open(filename, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
                
            stats["total"] += 1
            entry, parser_name, confidence = parse_with_confidence(line, resolver)
            
            if entry:
                stats["parsed"] += 1
                stats["parsers"][parser_name] = stats["parsers"].get(parser_name, 0) + 1
                
                # Process the parsed entry
                print(f"[{parser_name}] ({confidence:.2f}) {entry.to_dict()}")
            else:
                unparseable_lines.append(line)
                print(f"Could not parse: {line[:80]}...")
    
    # Report statistics
    print(f"\nParsing summary:")
    print(f"  Total lines: {stats['total']}")
    print(f"  Parsed successfully: {stats['parsed']} ({stats['parsed']/stats['total']*100:.1f}%)")
    print("  Parser distribution:")
    for parser, count in sorted(stats["parsers"].items(), key=lambda x: x[1], reverse=True):
        print(f"    {parser}: {count} ({count/stats['parsed']*100:.1f}%)")
    
    return stats, unparseable_lines