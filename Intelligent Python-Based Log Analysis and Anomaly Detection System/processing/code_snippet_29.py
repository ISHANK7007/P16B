from typing import Dict, List, Optional, Set, Union, Any, Callable
import asyncio
import os
from concurrent.futures import ThreadPoolExecutor
import mimetypes
from dataclasses import dataclass
import re

@dataclass
class LogSource:
    """Metadata about a log source."""
    source_id: str
    source_type: str  # file, stream, api, etc.
    path: Optional[str] = None
    format_hint: Optional[str] = None  # Optional hint about the log format
    credentials: Optional[Dict[str, str]] = None
    parser_chain: Optional[str] = None  # Parser chain to use
    metadata: Dict[str, Any] = None
    
    @property
    def filename(self) -> Optional[str]:
        """Get the filename from the path."""
        return os.path.basename(self.path) if self.path else None
    
    @property
    def extension(self) -> Optional[str]:
        """Get the file extension."""
        if not self.path:
            return None
        _, ext = os.path.splitext(self.path)
        return ext.lower() if ext else None

class LogIngestionController:
    """Controller for log ingestion with parser registry integration."""
    
    def __init__(self, 
                parser_resolver: OptimizedParserResolver,
                max_workers: int = 5,
                ingestion_batch_size: int = 1000):
        self.parser_resolver = parser_resolver
        self.max_workers = max_workers
        self.ingestion_batch_size = ingestion_batch_size
        self.worker_pool = ThreadPoolExecutor(max_workers=max_workers)
        
        # Format detection heuristics
        self.format_detectors = []
        self._initialize_format_detectors()
        
        # Stats tracking
        self.stats = {
            "files_processed": 0,
            "lines_processed": 0,
            "parse_failures": 0,
            "bytes_processed": 0
        }
        
    def _initialize_format_detectors(self) -> None:
        """Initialize format detection heuristics."""
        # Register file extension based detectors
        self.register_format_detector(
            lambda source: source.extension == '.json',
            'json'
        )
        self.register_format_detector(
            lambda source: source.extension in ('.log', '.txt') and source.filename and 'access' in source.filename.lower(),
            'apache_access'
        )
        self.register_format_detector(
            lambda source: source.extension in ('.log', '.txt') and source.filename and 'error' in source.filename.lower(),
            'apache_error'
        )
        self.register_format_detector(
            lambda source: source.extension == '.log' and source.filename and 'syslog' in source.filename.lower(),
            'syslog'
        )

        # Content-based format detection will be handled by the parser_resolver
    
    def register_format_detector(self, 
                                detector_func: Callable[[LogSource], bool],
                                format_hint: str,
                                chain_name: Optional[str] = None) -> None:
        """Register a format detector function."""
        self.format_detectors.append({
            'detector': detector_func,
            'format_hint': format_hint,
            'chain_name': chain_name
        })
    
    def detect_format(self, source: LogSource) -> Tuple[Optional[str], Optional[str]]:
        """
        Detect the log format and appropriate parser chain based on source metadata.
        
        Returns:
            Tuple of (format_hint, chain_name) or (None, None) if detection fails
        """
        # Use explicitly provided chain if available
        if source.parser_chain:
            return source.format_hint, source.parser_chain
            
        # Try format detectors
        for detector in self.format_detectors:
            if detector['detector'](source):
                return detector['format_hint'], detector['chain_name']
        
        # Default case
        return None, None
    
    def detect_format_from_content(self, 
                                   source: LogSource,
                                   sample_lines: List[str],
                                   min_confidence: float = 0.7) -> Tuple[Optional[str], Optional[str]]:
        """
        Detect format based on content samples.
        
        Returns:
            Tuple of (detected_format, chain_name) or (None, None) if detection fails
        """
        if not sample_lines:
            return None, None
            
        # Use the parser resolver to try parsing sample lines
        format_votes = {}
        
        for line in sample_lines:
            entry, trace = self.parser_resolver.base_resolver.resolve_with_trace(line, force_trace=True)
            
            if entry and trace.selected_parser and entry.confidence >= min_confidence:
                format_votes[trace.selected_parser] = format_votes.get(trace.selected_parser, 0) + 1
        
        if not format_votes:
            return None, None
            
        # Find the most common format
        detected_format, _ = max(format_votes.items(), key=lambda x: x[1])
        
        # Determine appropriate chain based on format
        chain_mapping = {
            'json': 'application',
            'syslog': 'linux_system',
            'apache_access': 'web_server',
            'apache_error': 'web_server',
            'nginx': 'web_server',
            'custom_app': 'application',
            'journald': 'linux_system'
        }
        
        chain_name = chain_mapping.get(detected_format)
        
        return detected_format, chain_name
    
    async def prepare_ingestion_job(self, source: LogSource) -> Dict[str, Any]:
        """
        Prepare a log ingestion job with the appropriate parser configuration.
        This method analyzes the source and determines the best parser strategy.
        """
        # Step 1: Try to detect format from metadata
        format_hint, chain_name = self.detect_format(source)
        
        # Step 2: If metadata detection failed, sample content for detection
        if not format_hint or not chain_name:
            sample_lines = await self._sample_log_content(source)
            content_format, content_chain = self.detect_format_from_content(source, sample_lines)
            
            # Use content-based detection if available
            if content_format:
                format_hint = content_format
                chain_name = content_chain
        
        # Step 3: Prepare the ingestion job configuration
        ingestion_config = {
            'source_id': source.source_id,
            'format': format_hint,
            'parser_chain': chain_name,
            # Include other job-specific parameters
            'batch_size': self.ingestion_batch_size,
            'content_based_detection': format_hint is None,  # Flag to enable runtime detection if needed
        }
        
        return ingestion_config
    
    async def _sample_log_content(self, source: LogSource, 
                               sample_size: int = 10) -> List[str]:
        """Sample log content for format detection."""
        samples = []
        
        if source.source_type == 'file' and source.path:
            try:
                with open(source.path, 'r', errors='replace') as f:
                    # Read a subset of lines for sampling
                    for _ in range(sample_size):
                        line = await asyncio.to_thread(f.readline)
                        if not line:
                            break
                        line = line.strip()
                        if line:
                            samples.append(line)
            except Exception as e:
                # Handle file reading errors
                print(f"Error sampling file {source.path}: {str(e)}")
        
        # Add handling for other source types (streams, APIs, etc.)
        
        return samples
    
    async def ingest_log_source(self, source: LogSource, 
                             output_queue: asyncio.Queue) -> Dict[str, Any]:
        """
        Ingest logs from a source using the appropriate parser.
        
        Args:
            source: The log source to ingest
            output_queue: Queue where parsed log entries will be placed
            
        Returns:
            Statistics about the ingestion job
        """
        # Prepare the ingestion configuration
        config = await self.prepare_ingestion_job(source)
        
        # Track stats for this job
        job_stats = {
            "source_id": source.source_id,
            "lines_processed": 0,
            "lines_parsed": 0,
            "parse_failures": 0,
            "bytes_processed": 0,
            "start_time": asyncio.get_event_loop().time()
        }
        
        # Process based on source type
        if source.source_type == 'file' and source.path:
            await self._ingest_file(
                source.path, 
                config.get('parser_chain'),
                config.get('content_based_detection', False),
                output_queue,
                job_stats
            )
        
        # Add other source types as needed
        
        # Record completion time
        job_stats["end_time"] = asyncio.get_event_loop().time()
        job_stats["duration"] = job_stats["end_time"] - job_stats["start_time"]
        
        # Update controller stats
        self.stats["files_processed"] += 1
        self.stats["lines_processed"] += job_stats["lines_processed"]
        self.stats["parse_failures"] += job_stats["parse_failures"]
        self.stats["bytes_processed"] += job_stats["bytes_processed"]
        
        return job_stats
    
    async def _ingest_file(self, 
                        file_path: str, 
                        parser_chain: Optional[str],
                        content_based_detection: bool,
                        output_queue: asyncio.Queue,
                        stats: Dict[str, Any]) -> None:
        """
        Ingest a log file with the specified parser configuration.
        
        Args:
            file_path: Path to the log file
            parser_chain: Name of the parser chain to use
            content_based_detection: Whether to use content-based parser selection
            output_queue: Queue to receive parsed entries
            stats: Statistics dictionary to update
        """
        if not os.path.exists(file_path):
            stats["error"] = f"File not found: {file_path}"
            return
        
        # Create processing pipeline components
        input_queue = asyncio.Queue(maxsize=10000)
        parallel_processor = ParallelLogProcessor(
            resolver=self.parser_resolver,
            batch_size=self.ingestion_batch_size
        )
        
        # Line reader task
        async def line_reader():
            try:
                with open(file_path, 'r', errors='replace') as f:
                    for line_num, line in enumerate(f):
                        line = line.strip()
                        stats["lines_processed"] += 1
                        stats["bytes_processed"] += len(line) + 1  # +1 for newline
                        
                        if line:
                            # Apply backpressure if necessary
                            while input_queue.qsize() >= 9000:
                                await asyncio.sleep(0.1)
                                
                            await input_queue.put((line_num, line))
                
                # Signal end of file
                await input_queue.put((None, None))
            except Exception as e:
                stats["error"] = f"Error reading file: {str(e)}"
                await input_queue.put((None, None))
        
        # Processor task
        async def processor():
            batch = []
            
            while True:
                try:
                    line_num, line = await input_queue.get()
                    input_queue.task_done()
                    
                    # Check for end of file marker
                    if line_num is None:
                        break
                        
                    batch.append((line_num, line))
                    
                    # Process batch if it's full
                    if len(batch) >= self.ingestion_batch_size:
                        await process_batch(batch)
                        batch = []
                
                except Exception as e:
                    stats["error"] = f"Processor error: {str(e)}"
                    break
            
            # Process any remaining items
            if batch:
                await process_batch(batch)
        
        # Batch processor helper
        async def process_batch(batch_items):
            # Extract just the log lines
            lines = [line for _, line in batch_items]
            
            # Process the batch
            try:
                entries = await parallel_processor.process_batch(lines)
                
                # Count successful parses
                stats["lines_parsed"] += len(entries)
                stats["parse_failures"] += len(lines) - len(entries)
                
                # Add line numbers to the entries
                for i, entry in enumerate(entries):
                    # Find the corresponding line number
                    line_num = batch_items[i][0] if i < len(batch_items) else -1
                    
                    # Add file and line metadata
                    if not hasattr(entry, "source_metadata"):
                        entry.source_metadata = {}
                    
                    entry.source_metadata.update({
                        "file": file_path,
                        "line_number": line_num
                    })
                    
                    # Put in output queue
                    await output_queue.put(entry)
            
            except Exception as e:
                stats["error"] = f"Batch processing error: {str(e)}"
                stats["parse_failures"] += len(batch_items)
        
        # Start the processing tasks
        await asyncio.gather(line_reader(), processor())