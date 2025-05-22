class ParserDebugConsole:
    """Interactive console for debugging parser issues."""
    
    def __init__(self, resolver: ParserResolver):
        self.resolver = resolver
        self.registry = ParserRegistry
    
    def analyze_log(self, log_line: str) -> Dict[str, Any]:
        """Analyze a log line with all available parsers and report detailed results."""
        # Force tracing even if normally disabled
        _, trace = self.resolver.resolve_with_trace(log_line, force_trace=True)
        
        # Analysis results
        results = {
            "raw_log": log_line,
            "trace_id": trace.trace_id,
            "parser_attempts": len(trace.attempts),
            "successful_parsers": [a.parser_name for a in trace.attempts 
                                if a.result == ParserResult.SUCCESS],
            "partial_parsers": [a.parser_name for a in trace.attempts 
                              if a.result == ParserResult.PARTIAL],
            "failed_parsers": [a.parser_name for a in trace.attempts 
                             if a.result in (ParserResult.ERROR, ParserResult.REJECTED)]
        }
        
        # Field extraction analysis
        field_extractions = {}
        field_conflicts = {}
        
        # Analyze extracted fields across parsers
        for attempt in trace.attempts:
            if attempt.result not in (ParserResult.SUCCESS, ParserResult.PARTIAL):
                continue
                
            # Get the parsed entry for this attempt
            parser_class = self.registry.get_parser(attempt.parser_name)
            if not parser_class:
                continue
                
            parser = parser_class()
            entry = parser.parse(log_line)
            if not entry:
                continue
                
            # Track fields extracted by this parser
            for field_name, field_value in entry.fields.items():
                if field_name not in field_extractions:
                    field_extractions[field_name] = []
                
                # Record this extraction
                field_extractions[field_name].append({
                    "parser": attempt.parser_name,
                    "value": field_value,
                    "confidence": attempt.confidence
                })
        
        # Identify conflicts - fields extracted differently by multiple parsers
        for field_name, extractions in field_extractions.items():
            if len(extractions) <= 1:
                continue
                
            # Check if there are different values
            values = set(str(e["value"]) for e in extractions)
            if len(values) > 1:
                field_conflicts[field_name] = extractions
        
        # Add field analysis to results
        results["extracted_fields"] = field_extractions
        results["field_conflicts"] = field_conflicts
        results["conflict_count"] = len(field_conflicts)
        
        return results
    
    def generate_report(self, log_line: str) -> str:
        """Generate a human-readable report of parser analysis."""
        analysis = self.analyze_log(log_line)
        
        report = [
            "====== PARSER DEBUG REPORT ======",
            f"Log: {analysis['raw_log'][:100]}{'...' if len(analysis['raw_log']) > 100 else ''}",
            f"Trace ID: {analysis['trace_id']}",
            f"Parser attempts: {analysis['parser_attempts']}",
            "",
            "--- PARSER RESULTS ---",
            f"Successful: {', '.join(analysis['successful_parsers']) or 'None'}",
            f"Partial: {', '.join(analysis['partial_parsers']) or 'None'}",
            f"Failed: {', '.join(analysis['failed_parsers']) or 'None'}",
            "",
        ]
        
        if analysis["field_conflicts"]:
            report.append("--- FIELD CONFLICTS ---")
            for field_name, extractions in analysis["field_conflicts"].items():
                report.append(f"Field '{field_name}' has conflicts:")
                for ext in extractions:
                    report.append(f"  {ext['parser']} ({ext['confidence']:.4f}): {ext['value']}")
                report.append("")
        
        report.append("--- ALL EXTRACTED FIELDS ---")
        for field_name, extractions in analysis["extracted_fields"].items():
            if field_name in analysis["field_conflicts"]:
                report.append(f"{field_name} [CONFLICT]:")
            else:
                report.append(f"{field_name}:")
            
            for ext in extractions:
                report.append(f"  {ext['parser']} ({ext['confidence']:.4f}): {ext['value']}")
            
        return "\n".join(report)