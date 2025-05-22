def parse_with_confidence(log_line: str, resolver: ParserResolver, min_confidence: float = 0.5) -> Optional[ParsedLogEntry]:
    """
    Parse a log line using confidence-based resolution across multiple parsers.
    
    Args:
        log_line: The log line to parse
        resolver: The ParserResolver instance
        min_confidence: Minimum confidence threshold to accept a result
        
    Returns:
        The best parsed entry or None if no parser met the confidence threshold
    """
    best_entry = None
    best_parser = None
    best_confidence = 0.0
    
    # Try all parsers and track the one with highest confidence
    for parser_name, parser_class in ParserRegistry.get_all_parsers().items():
        parser = parser_class()
        if not parser.can_parse(log_line):
            continue
            
        entry = parser.parse(log_line)
        if not entry:
            continue
            
        confidence = parser.confidence(log_line, entry)
        if confidence > best_confidence:
            best_confidence = confidence
            best_entry = entry
            best_parser = parser_name
    
    # Only return entries that meet the minimum confidence threshold
    if best_confidence >= min_confidence:
        return best_entry, best_parser, best_confidence
    
    return None, None, 0.0