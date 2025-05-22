class AdaptiveLogProcessingPipeline:
    """
    End-to-end pipeline that processes logs through appropriate parsers,
    with dynamic selection and optimization.
    """
    
    def __init__(self):
        # Initialize parser registry
        self.registry = ParserRegistry()
        
        # Discover available parsers
        self.registry.discover_parsers()
        
        # Create resolver components
        self.base_resolver = ParserResolver(debug=False, trace_all=False)
        self.optimized_resolver = OptimizedParserResolver(self.base_resolver)
        
        # Create chain selector
        self.chain_selector = ParserChainSelector(self.base_resolver)
        
        # Create ingestion controller
        self.ingestion_controller = LogIngestionController(self.optimized_resolver)
        
        # Create streaming adapter
        self.streaming_adapter = StreamingParserAdapter(
            self.ingestion_controller,
            self.chain_selector
        )
        
        # Format cache for optimization
        self.format_cache = FormatCache(max_size=50000)
        
        # Setup format detector heuristics
        self._setup_format_detectors()
    
    def _setup_format_detectors(self) -> None:
        """Setup format detector heuristics."""
        # Register common format detectors
        self.streaming_adapter.register_format_detector(
            lambda source: source.path and source.path.endswith('.json'),
            lambda: 'json'
        )
        
        self.streaming_adapter.register_format_detector(
            lambda source: source.path and '/var/log/syslog' in source.path,
            lambda: 'syslog'
        )
        
        # Content analysis for ambiguous formats
        self.streaming_adapter.register_content_analyzer(
            lambda lines: any('<html' in line.lower() for line in lines),
            lambda: 'html_error'
        )
    
    async def process_log_source(self, 
                               source: LogSource,
                               handler: Callable[[ParsedLogEntry], Awaitable[None]]) -> Dict[str, Any]:
        """
        Process a log source through the appropriate parser.
        
        Args:
            source: Log source description
            handler: Async function to handle each parsed entry
            
        Returns:
            Processing statistics
        """
        # Create parser stream
        task = await self.streaming_adapter.create_parser_stream(source, handler)
        
        # Wait for processing to complete
        await task
        
        # Return statistics
        return self.ingestion_controller.stats
    
    async def process_multiple_sources(self,
                                    sources: List[LogSource],
                                    handler: Callable[[ParsedLogEntry], Awaitable[None]],
                                    max_concurrent: int = 5) -> Dict[str, Any]:
        """
        Process multiple log sources concurrently.
        
        Args:
            sources: List of log sources
            handler: Async function to handle each parsed entry
            max_concurrent: Maximum number of sources to process concurrently
            
        Returns:
            Processing statistics
        """
        # Use semaphore to limit concurrency
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_with_semaphore(source):
            async with semaphore:
                return await self.process_log_source(source, handler)
        
        # Process all sources
        tasks = [process_with_semaphore(source) for source in sources]
        results = await asyncio.gather(*tasks)
        
        # Aggregate statistics
        stats = {
            "sources_processed": len(sources),
            "total_lines_processed": sum(r.get("lines_processed", 0) for r in results),
            "total_lines_parsed": sum(r.get("lines_parsed", 0) for r in results),
            "total_parse_failures": sum(r.get("parse_failures", 0) for r in results),
            "total_bytes_processed": sum(r.get("bytes_processed", 0) for r in results),
        }
        
        return stats