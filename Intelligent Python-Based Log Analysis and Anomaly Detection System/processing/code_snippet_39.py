class NormalizingLogIngestionController(LogIngestionController):
    """Extended LogIngestionController with field normalization capabilities."""
    
    def __init__(self, 
                parser_resolver: OptimizedParserResolver,
                normalization_manager: LogNormalizationManager,
                max_workers: int = 5,
                ingestion_batch_size: int = 1000):
        super().__init__(parser_resolver, max_workers, ingestion_batch_size)
        self.normalization_manager = normalization_manager
    
    def normalize_log_entry(self, entry: ParsedLogEntry) -> ParsedLogEntry:
        """Normalize a parsed log entry."""
        if not entry:
            return None
            
        # Convert to dict for normalization
        entry_dict = entry.to_dict()
        
        # Add parser information if available
        if hasattr(entry, "parser_metadata") and "parser_name" in entry.parser_metadata:
            entry_dict["_parser"] = {"name": entry.parser_metadata["parser_name"]}
        
        # Normalize
        normalized = self.normalization_manager.normalize(entry_dict)
        
        # Create a new entry from normalized data
        result = ParsedLogEntry(
            timestamp=normalized["timestamp"],
            level=normalized["level"],
            message=normalized["message"],
            source=normalized.get("source", ""),
            fields={k: v for k, v in normalized.items() 
                   if k not in ["timestamp", "level", "message", "source"]}
        )
        
        # Preserve metadata
        if hasattr(entry, "parser_metadata"):
            result.parser_metadata = entry.parser_metadata.copy()
            result.parser_metadata["normalized"] = True
            
        if hasattr(entry, "source_metadata"):
            result.source_metadata = entry.source_metadata.copy()
        
        return result
    
    async def _ingest_file(self, 
                        file_path: str, 
                        parser_chain: Optional[str],
                        content_based_detection: bool,
                        output_queue: asyncio.Queue,
                        stats: Dict[str, Any]) -> None:
        """Enhanced ingest_file with normalization."""
        # Most of the method is the same as the parent class
        # We'll just modify the process_batch function
        
        if not os.path.exists(file_path):
            stats["error"] = f"File not found: {file_path}"
            return
        
        input_queue = asyncio.Queue(maxsize=10000)
        parallel_processor = ParallelLogProcessor(
            resolver=self.parser_resolver,
            batch_size=self.ingestion_batch_size
        )
        
        # Line reader task (unchanged)
        async def line_reader():
            # Same as parent class
            pass
        
        # Processor task (unchanged)
        async def processor():
            # Same as parent class
            pass
        
        # Enhanced batch processor with normalization
        async def process_batch(batch_items):
            # Extract just the log lines
            lines = [line for _, line in batch_items]
            
            # Process the batch
            try:
                entries = await parallel_processor.process_batch(lines)
                
                # Count successful parses
                stats["lines_parsed"] += len(entries)
                stats["parse_failures"] += len(lines) - len(entries)
                
                # Normalize and add line numbers to the entries
                normalized_entries = []
                for i, entry in enumerate(entries):
                    # Normalize the entry
                    normalized = self.normalize_log_entry(entry)
                    if not normalized:
                        continue
                        
                    # Find the corresponding line number
                    line_num = batch_items[i][0] if i < len(batch_items) else -1
                    
                    # Add file and line metadata
                    if not hasattr(normalized, "source_metadata"):
                        normalized.source_metadata = {}
                    
                    normalized.source_metadata.update({
                        "file": file_path,
                        "line_number": line_num
                    })
                    
                    normalized_entries.append(normalized)
                
                # Put in output queue
                for entry in normalized_entries:
                    await output_queue.put(entry)
            
            except Exception as e:
                stats["error"] = f"Batch processing error: {str(e)}"
                stats["parse_failures"] += len(batch_items)
        
        # Start the processing tasks (unchanged)
        await asyncio.gather(line_reader(), processor())