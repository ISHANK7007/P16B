from enum import Enum

class ConflictResolutionStrategy(Enum):
    HIGHEST_CONFIDENCE = "highest_confidence"
    MOST_FIELDS = "most_fields"
    FIRST_MATCH = "first_match"
    HEURISTIC = "heuristic"
    MERGE = "merge"

class ConflictResolver:
    """Specialized resolver for handling parser conflicts."""
    
    def __init__(self, 
                strategy: ConflictResolutionStrategy = ConflictResolutionStrategy.HIGHEST_CONFIDENCE,
                min_merge_confidence: float = 0.3):
        self.strategy = strategy
        self.min_merge_confidence = min_merge_confidence
    
    def resolve(self, 
               log_line: str, 
               results: List[Tuple[str, ParsedLogEntry, float]]) -> Tuple[str, ParsedLogEntry, str]:
        """
        Resolve conflicts between multiple parser results.
        
        Returns:
            Tuple of (selected_parser_name, merged_entry, resolution_description)
        """
        if not results:
            raise ValueError("No results to resolve")
            
        if len(results) == 1:
            parser_name, entry, _ = results[0]
            return parser_name, entry, "Single result, no conflict"
            
        # Sort by confidence (highest first)
        results.sort(key=lambda x: x[2], reverse=True)
        
        if self.strategy == ConflictResolutionStrategy.HIGHEST_CONFIDENCE:
            # Simply take the highest confidence result
            parser_name, entry, confidence = results[0]
            return parser_name, entry, f"Selected highest confidence ({confidence:.4f})"
            
        elif self.strategy == ConflictResolutionStrategy.MOST_FIELDS:
            # Take the result with the most extracted fields
            results.sort(key=lambda x: len(x[1].fields), reverse=True)
            parser_name, entry, _ = results[0]
            return parser_name, entry, f"Selected most fields ({len(entry.fields)})"
            
        elif self.strategy == ConflictResolutionStrategy.FIRST_MATCH:
            # Take the first result (as ordered in the parser chain)
            parser_name, entry, _ = results[0]
            return parser_name, entry, "Selected first match in chain"
            
        elif self.strategy == ConflictResolutionStrategy.MERGE:
            # Attempt to merge fields from multiple parsers
            return self._merge_results(results)
            
        elif self.strategy == ConflictResolutionStrategy.HEURISTIC:
            # Use a combination of heuristics
            return self._heuristic_resolution(log_line, results)
            
        # Default to highest confidence
        parser_name, entry, confidence = results[0]
        return parser_name, entry, f"Default to highest confidence ({confidence:.4f})"
    
    def _merge_results(self, 
                      results: List[Tuple[str, ParsedLogEntry, float]]) -> Tuple[str, ParsedLogEntry, str]:
        """
        Merge fields from multiple parser results.
        Only parsers with confidence above min_merge_confidence are considered.
        Fields from higher confidence parsers take precedence.
        """
        if not results:
            raise ValueError("No results to merge")
            
        # Filter results by minimum confidence
        valid_results = [(name, entry, conf) for name, entry, conf in results 
                         if conf >= self.min_merge_confidence]
        
        if not valid_results:
            # Fall back to highest confidence if no results meet the threshold
            parser_name, entry, confidence = results[0]
            return parser_name, entry, f"No results meet merge threshold, using highest confidence ({confidence:.4f})"
        
        # Start with the highest confidence result
        best_parser, merged_entry, best_conf = valid_results[0]
        
        # Create a new ParsedLogEntry with copied data
        merged = ParsedLogEntry(
            timestamp=merged_entry.timestamp,
            level=merged_entry.level,
            message=merged_entry.message,
            source=merged_entry.source,
            fields=merged_entry.fields.copy()
        )
        
        # Track parsers that contributed to the merge
        contributing_parsers = [best_parser]
        
        # Merge fields from other parsers
        for parser_name, entry, _ in valid_results[1:]:
            # Don't overwrite existing fields from higher confidence parsers
            new_fields = {k: v for k, v in entry.fields.items() if k not in merged.fields}
            
            if new_fields:
                merged.fields.update(new_fields)
                contributing_parsers.append(parser_name)
        
        # Set metadata
        parser_description = "merged"
        resolution_description = f"Merged fields from {len(contributing_parsers)} parsers: {', '.join(contributing_parsers)}"
        
        merged.parser_metadata = {
            "parser_name": parser_description,
            "source_parsers": contributing_parsers,
            "confidence": best_conf,  # Use highest confidence
            "is_merged": True
        }
        
        return parser_description, merged, resolution_description
    
    def _heuristic_resolution(self, 
                            log_line: str, 
                            results: List[Tuple[str, ParsedLogEntry, float]]) -> Tuple[str, ParsedLogEntry, str]:
        """
        Use multiple heuristics to select the best result:
        - Weight confidence scores
        - Consider number and quality of extracted fields
        - Examine completeness of timestamp, level, and message
        - Check for special patterns in the log line
        """
        # This would be a more complex implementation
        # For simplicity, just use highest confidence for now
        parser_name, entry, confidence = results[0]
        return parser_name, entry, f"Heuristic selection (confidence: {confidence:.4f})"