class BatchEditProcessor:
    """
    Processes edit operations in batches to reduce overhead and
    optimize performance during high-frequency editing sessions.
    """
    def __init__(self, max_batch_size=50, max_wait_ms=100):
        self.max_batch_size = max_batch_size
        self.max_wait_ms = max_wait_ms
        self.current_batch = []
        self.batch_lock = threading.RLock()
        self.processing = False
        self.scheduler = BatchScheduler()
        
    async def queue_edit(self, edit_operation):
        """Queue an edit for batch processing"""
        with self.batch_lock:
            # Add to current batch
            self.current_batch.append(edit_operation)
            
            # If batch is full, process immediately
            if len(self.current_batch) >= self.max_batch_size:
                await self._process_current_batch()
                return
                
            # Schedule processing if not already scheduled
            if not self.processing:
                self.processing = True
                self.scheduler.schedule(
                    self._process_current_batch,
                    delay_ms=self.max_wait_ms
                )
                
    async def _process_current_batch(self):
        """Process the current batch of edits"""
        with self.batch_lock:
            batch_to_process = self.current_batch
            self.current_batch = []
            self.processing = False
            
        if not batch_to_process:
            return
            
        # Group edits by session
        edits_by_session = {}
        for edit in batch_to_process:
            session_id = edit.session_id
            if session_id not in edits_by_session:
                edits_by_session[session_id] = []
            edits_by_session[session_id].append(edit)
            
        # Process each session's edits
        for session_id, edits in edits_by_session.items():
            await self._process_session_edits(session_id, edits)
            
    async def _process_session_edits(self, session_id, edits):
        """Process all edits for a specific session"""
        # Optimize edit sequence
        optimized_edits = self._optimize_edit_sequence(edits)
        
        # Execute optimized edits
        for edit in optimized_edits:
            await self._execute_edit(session_id, edit)
            
    def _optimize_edit_sequence(self, edits):
        """Optimize a sequence of edits to reduce redundant operations"""
        if not edits:
            return []
            
        # Sort by position (for non-overlapping edits)
        edits.sort(key=lambda e: e.position)
        
        # Merge adjacent/overlapping edits of the same type
        optimized = []
        current = edits[0]
        
        for next_edit in edits[1:]:
            if (current.operation_type == next_edit.operation_type and
                current.position + len(current.content) >= next_edit.position):
                # Merge edits
                overlap = current.position + len(current.content) - next_edit.position
                if overlap > 0:
                    merged_content = current.content + next_edit.content[overlap:]
                else:
                    merged_content = current.content + next_edit.content
                    
                current = EditOperation(
                    operation_type=current.operation_type,
                    position=current.position,
                    content=merged_content
                )
            else:
                optimized.append(current)
                current = next_edit
                
        optimized.append(current)
        return optimized