# Example: Setting up the resolver with advanced debugging
resolver = ParserResolver(
    debug=True,  # Enable debug logging
    trace_all=False,  # Only trace when conflicts arise
    min_confidence_threshold=0.6,  # Minimum confidence to consider a result valid
    store_traces=True,  # Store traces for later inspection
    trace_store_limit=1000  # Maximum number of traces to store
)

# Set up parser chains
setup_parser_chains(resolver)

# Create the audit log
audit_log = ParserAuditLog("parser_audit.db")

# Example: Processing a log line with full debugging
def process_log_with_debugging(log_line: str) -> None:
    # Parse with tracing
    entry, trace = resolver.resolve_with_trace(log_line, force_trace=True)
    
    # Log the trace to the audit database
    audit_log.log_trace(trace)
    
    if trace.conflict_detected:
        # Generate a detailed debug report for conflicts
        debug_console = ParserDebugConsole(resolver)
        report = debug_console.generate_report(log_line)
        print(report)
    
    return entry

# Example: Processing a batch of logs with conflict detection
def process_log_batch(logs: List[str]) -> List[Tuple[ParsedLogEntry, bool]]:
    results = []
    
    for log_line in logs:
        entry, trace = resolver.resolve_with_trace(log_line)
        
        # Only create full traces for conflicting parsers to save resources
        if trace.conflict_detected:
            # Store the trace
            audit_log.log_trace(trace)
            
            # Flag this entry as having a conflict
            results.append((entry, True))
        else:
            results.append((entry, False))
    
    return results

# Example: Analyzing parser performance
def analyze_parser_performance() -> None:
    performance = audit_log.get_parser_performance(days=7)
    
    print("Parser performance over the past 7 days:")
    for parser, stats in performance.items():
        print(f"{parser}:")
        print(f"  Success rate: {stats['success_rate']:.2%}")
        print(f"  Attempts: {stats['attempts']}")
        print(f"  Avg confidence: {stats['avg_confidence']:.4f}")
        print(f"  Avg time: {stats['avg_time_ms']:.2f}ms")
    
    # Find recurring conflicts
    conflicts = audit_log.get_recurring_conflicts(days=7, min_occurrences=3)
    
    if conflicts:
        print("\nRecurring parser conflicts:")
        for conflict in conflicts:
            print(f"  Hash: {conflict['log_hash']}")
            print(f"  Occurrences: {conflict['occurrences']}")
            print(f"  Conflicting parsers: {conflict['parsers']}")