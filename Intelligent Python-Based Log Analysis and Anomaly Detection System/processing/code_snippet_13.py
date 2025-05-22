import time
import uuid
import logging
from typing import Dict, List, Optional, Tuple, Type, Set

class DebugLogger:
    """Custom logger for parser debugging."""
    
    def __init__(self, enabled: bool = False, level: int = logging.INFO):
        self.enabled = enabled
        self.logger = logging.getLogger("parser.debug")
        self.logger.setLevel(level)
        
        # Add a handler if not already present
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def debug(self, message: str) -> None:
        """Log a debug message if debugging is enabled."""
        if self.enabled:
            self.logger.debug(message)
    
    def info(self, message: str) -> None:
        """Log an info message if debugging is enabled."""
        if self.enabled:
            self.logger.info(message)
    
    def warning(self, message: str) -> None:
        """Log a warning message if debugging is enabled."""
        if self.enabled:
            self.logger.warning(message)
    
    def error(self, message: str) -> None:
        """Log an error message if debugging is enabled."""
        if self.enabled:
            self.logger.error(message)
            
    def log_trace(self, trace: ParserTrace) -> None:
        """Log a parser trace."""
        if not self.enabled:
            return
            
        self.info(f"Parser trace {trace.trace_id}:")
        self.info(f"  Raw log: {trace.raw_log[:100]}{'...' if len(trace.raw_log) > 100 else ''}")
        self.info(f"  Selected parser: {trace.selected_parser}")
        self.info(f"  Total parsing time: {trace.parsing_time_ms:.2f}ms")
        self.info(f"  Parser attempts: {len(trace.attempts)}")
        
        if trace.conflict_detected:
            self.warning(f"  Conflicts detected! Resolution: {trace.conflict_resolution}")
            
        # Log each attempt
        for i, attempt in enumerate(trace.attempts):
            if attempt.result == ParserResult.SUCCESS:
                self.info(f"  [{i+1}] {attempt.parser_name}: SUCCESS (confidence: {attempt.confidence:.4f})")
            elif attempt.result == ParserResult.PARTIAL:
                self.info(f"  [{i+1}] {attempt.parser_name}: PARTIAL (confidence: {attempt.confidence:.4f})")
            elif attempt.result == ParserResult.ERROR:
                self.error(f"  [{i+1}] {attempt.parser_name}: ERROR - {attempt.error_message}")
            elif attempt.result == ParserResult.REJECTED:
                self.debug(f"  [{i+1}] {attempt.parser_name}: REJECTED - {attempt.rejected_reason}")
            else:
                self.debug(f"  [{i+1}] {attempt.parser_name}: {attempt.result}")

class ParserResolver:
    """Enhanced resolver with debugging capabilities."""
    
    def __init__(self, 
                debug: bool = False, 
                trace_all: bool = False,
                min_confidence_threshold: float = 0.6,
                store_traces: bool = False,
                trace_store_limit: int = 1000):
        self._chains: Dict[str, ParserChainConfig] = {}
        self._default_chain: Optional[str] = None
        self.debug = DebugLogger(enabled=debug)
        self.trace_all = trace_all
        self.min_confidence_threshold = min_confidence_threshold
        self.store_traces = store_traces
        self.trace_store: Dict[str, ParserTrace] = {}
        self.trace_store_limit = trace_store_limit
        
    def resolve_with_trace(self, 
                         log_line: str, 
                         chain_name: Optional[str] = None,
                         force_trace: bool = False) -> Tuple[Optional[ParsedLogEntry], ParserTrace]:
        """
        Resolve the best parser for a log line and record the complete parsing trace.
        
        Args:
            log_line: The log line to parse
            chain_name: Optional name of the parser chain to use
            force_trace: Force trace creation even if tracing is disabled
            
        Returns:
            Tuple of (parsed_entry, trace)
        """
        start_time = time.time()
        
        # Create a trace if tracing is enabled or forced
        should_trace = self.trace_all or force_trace
        trace = ParserTrace(
            trace_id=str(uuid.uuid4()),
            raw_log=log_line,
            timestamp=datetime.now()
        )
        
        # Get the chain to use
        chain = None
        if chain_name:
            chain = self.get_chain(chain_name)
        if not chain and self._default_chain:
            chain = self.get_chain(self._default_chain)
        
        # Try parsers in chain or all parsers
        parser_names = chain.parsers if chain else list(ParserRegistry.get_all_parsers().keys())
        
        # Track results from all parsers
        successful_results: List[Tuple[str, ParsedLogEntry, float]] = []
        
        for parser_name in parser_names:
            parser_class = ParserRegistry.get_parser(parser_name)
            if not parser_class:
                if should_trace:
                    trace.add_attempt(ParserAttempt(
                        parser_name=parser_name,
                        result=ParserResult.SKIPPED,
                        confidence=0.0,
                        duration_ms=0.0,
                        rejected_reason="Parser not found in registry"
                    ))
                continue
                
            # Create parser instance
            parser = parser_class()
            
            # Skip if parser can't handle this log (fast check)
            if not parser.can_parse(log_line):
                if should_trace:
                    trace.add_attempt(ParserAttempt(
                        parser_name=parser_name,
                        result=ParserResult.SKIPPED,
                        confidence=0.0,
                        duration_ms=0.0,
                        rejected_reason="Initial pattern match failed"
                    ))
                continue
                
            # Attempt to parse
            parser_start = time.time()
            try:
                entry = parser.parse(log_line)
                parser_duration = (time.time() - parser_start) * 1000  # ms
                
                if entry is None:
                    # Parser declined to parse despite pattern match
                    if should_trace:
                        trace.add_attempt(ParserAttempt(
                            parser_name=parser_name,
                            result=ParserResult.REJECTED,
                            confidence=0.0,
                            duration_ms=parser_duration,
                            rejected_reason="Parser returned None"
                        ))
                    continue
                
                # Validate the entry
                if not parser.validate(entry):
                    if should_trace:
                        trace.add_attempt(ParserAttempt(
                            parser_name=parser_name,
                            result=ParserResult.REJECTED,
                            confidence=0.0, 
                            duration_ms=parser_duration,
                            rejected_reason="Entry failed validation"
                        ))
                    continue
                
                # Get confidence score
                confidence = parser.confidence(log_line, entry)
                
                # Record successful parse
                if should_trace:
                    trace.add_attempt(ParserAttempt(
                        parser_name=parser_name,
                        result=ParserResult.SUCCESS if confidence >= self.min_confidence_threshold else ParserResult.PARTIAL,
                        confidence=confidence,
                        duration_ms=parser_duration,
                        extracted_fields=set(entry.fields.keys())
                    ))
                
                # Only consider results with minimum confidence
                if confidence >= self.min_confidence_threshold:
                    successful_results.append((parser_name, entry, confidence))
                
            except Exception as e:
                parser_duration = (time.time() - parser_start) * 1000  # ms
                if should_trace:
                    trace.add_attempt(ParserAttempt(
                        parser_name=parser_name,
                        result=ParserResult.ERROR,
                        confidence=0.0,
                        duration_ms=parser_duration,
                        error_message=str(e)
                    ))
                    
                self.debug.error(f"Parser {parser_name} raised exception: {str(e)}")
        
        # Determine the best result
        best_entry: Optional[ParsedLogEntry] = None
        best_parser: Optional[str] = None
        best_confidence = 0.0
        
        # If we have multiple successful results, we have a conflict
        if len(successful_results) > 1:
            conflict_detected = True
            
            # Sort by confidence score (highest first)
            successful_results.sort(key=lambda x: x[2], reverse=True)
            
            # Get the highest confidence result
            best_parser, best_entry, best_confidence = successful_results[0]
            
            # Record conflict resolution
            if should_trace:
                trace.conflict_detected = True
                trace.conflict_resolution = f"Selected highest confidence parser: {best_parser} ({best_confidence:.4f})"
                
                # Log the conflict
                conflict_msg = f"Parser conflict for log: {log_line[:100]}..."
                self.debug.warning(conflict_msg)
                self.debug.warning(f"Selected {best_parser} (confidence: {best_confidence:.4f}) from {len(successful_results)} parsers")
                for name, _, conf in successful_results:
                    self.debug.warning(f"  {name}: confidence {conf:.4f}")
        
        elif len(successful_results) == 1:
            # Just one parser succeeded
            best_parser, best_entry, best_confidence = successful_results[0]
        
        # Update trace with final results
        if should_trace:
            trace.selected_parser = best_parser
            trace.parsing_time_ms = (time.time() - start_time) * 1000
            
            # Store the trace if requested
            if self.store_traces:
                if len(self.trace_store) >= self.trace_store_limit:
                    # Remove oldest trace if we hit the limit
                    oldest_key = next(iter(self.trace_store))
                    del self.trace_store[oldest_key]
                
                self.trace_store[trace.trace_id] = trace
            
            # Log the complete trace
            self.debug.log_trace(trace)
        
        # Add metadata to the entry if we have a result
        if best_entry:
            best_entry.parser_metadata = {
                "parser_name": best_parser,
                "confidence": best_confidence,
                "parsing_time_ms": (time.time() - start_time) * 1000
            }
            
            # Add trace information if available
            if should_trace:
                best_entry.parser_metadata["trace_id"] = trace.trace_id
                best_entry.parser_metadata["conflicts_detected"] = trace.conflict_detected
                
                # If conflicts detected, add information about competing parsers
                if trace.conflict_detected:
                    best_entry.parser_metadata["competing_parsers"] = [
                        {"name": name, "confidence": conf}
                        for name, _, conf in successful_results[1:]  # Skip the best one
                    ]
            
        return best_entry, trace
    
    def get_trace(self, trace_id: str) -> Optional[ParserTrace]:
        """Get a stored trace by ID."""
        return self.trace_store.get(trace_id)
    
    def get_recent_traces(self, limit: int = 10) -> List[ParserTrace]:
        """Get the most recent traces."""
        return list(self.trace_store.values())[-limit:]