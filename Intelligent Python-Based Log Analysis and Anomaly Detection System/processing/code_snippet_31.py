class StreamingParserAdapter:
    """
    Adapter that connects LogIngestionController to the dynamic parser registry.
    Handles streaming logs through appropriate parsers based on source metadata
    and content analysis.
    """
    
    def __init__(self, 
                ingestion_controller: LogIngestionController,
                chain_selector: ParserChainSelector):
        self.ingestion_controller = ingestion_controller
        self.chain_selector = chain_selector
        
        # Format detector registry
        self.format_detectors = []
        self.content_analyzers = []
        
        # Initialize default detectors and analyzers
        self._init_detectors()
        
    def _init_detectors(self) -> None:
        """Initialize default format detectors."""
        # File extension detectors
        self.register_format_detector(
            lambda source: source.extension == '.json',
            lambda: 'json'
        )
        
        # Filename pattern detectors
        self.register_format_detector(
            lambda source: source.filename and 'access' in source.filename.lower(),
            lambda: 'apache_access'
        )
        
        # Content analyzers for the first few lines
        self.register_content_analyzer(
            lambda lines: any(line.strip().startswith('{') and line.strip().endswith('}') for line in lines),
            lambda: 'json'
        )
        
        self.register_content_analyzer(
            lambda lines: any(re.search(r'\d+\.\d+\.\d+\.\d+ - -', line) for line in lines),
            lambda: 'apache_access'
        )
    
    def register_format_detector(self, condition: Callable[[LogSource], bool],
                               format_provider: Callable[[], str]) -> None:
        """Register a format detector based on source metadata."""
        self.format_detectors.append((condition, format_provider))
    
    def register_content_analyzer(self, condition: Callable[[List[str]], bool],
                                format_provider: Callable[[], str]) -> None:
        """Register a content analyzer for format detection."""
        self.content_analyzers.append((condition, format_provider))
    
    def detect_format(self, source: LogSource, sample_lines: List[str] = None) -> Optional[str]:
        """
        Detect the log format based on source metadata and optional content samples.
        
        Returns:
            Detected format or None if uncertain
        """
        # First check source metadata using format detectors
        for condition, format_provider in self.format_detectors:
            if condition(source):
                return format_provider()
        
        # If we have sample lines, use content analyzers
        if sample_lines:
            for condition, format_provider in self.content_analyzers:
                if condition(sample_lines):
                    return format_provider()
        
        # Unable to determine format
        return None
    
    async def create_parser_stream(self, 
                                source: LogSource,
                                output_handler: Callable[[ParsedLogEntry], Awaitable[None]]) -> asyncio.Task:
        """
        Create a streaming parser task for the given source.
        
        Args:
            source: The log source to parse
            output_handler: Async function to handle each parsed entry
            
        Returns:
            An asyncio Task representing the streaming parser
        """
        # Determine the optimal parser chain
        sample_lines = await self.ingestion_controller._sample_log_content(source)
        
        # Detect format if not already specified
        if not source.format_hint:
            source.format_hint = self.detect_format(source, sample_lines)
        
        # Select parser chain
        chain_name = await self.chain_selector.select_chain(source, sample_lines)
        
        # Create a queue for parsed entries
        parsed_queue = asyncio.Queue()
        
        # Consumer task to handle parsed entries
        async def consumer():
            while True:
                entry = await parsed_queue.get()
                
                # Check for sentinel value
                if entry is None:
                    parsed_queue.task_done()
                    break
                
                # Process the entry
                await output_handler(entry)
                parsed_queue.task_done()
        
        # Start consumer task
        consumer_task = asyncio.create_task(consumer())
        
        # Start ingestion
        ingestion_task = asyncio.create_task(
            self.ingestion_controller.ingest_log_source(source, parsed_queue)
        )
        
        # When ingestion is complete, signal the end to the consumer
        async def finalize():
            try:
                await ingestion_task
            finally:
                await parsed_queue.put(None)
                await consumer_task
        
        # Create and return the main task
        return asyncio.create_task(finalize())