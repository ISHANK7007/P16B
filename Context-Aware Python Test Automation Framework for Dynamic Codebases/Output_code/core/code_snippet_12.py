class SynchronizationOrchestrator:
    """Orchestrates bidirectional flow between prompt edits and token generation"""
    def __init__(self, cursor, llm_client):
        self.cursor = cursor
        self.llm_client = llm_client
        self.edit_queue = Queue()
        self.token_queue = Queue()
        self.sync_lock = threading.RLock()
        self.event_bus = EventBus()
        
    async def process_edit(self, edit_operation):
        """Process an edit from the agent side"""
        with self.sync_lock:
            # Check for conflicts with rollback guards
            conflicts = self._check_rollback_conflicts(edit_operation)
            if conflicts:
                return self._handle_edit_conflicts(edit_operation, conflicts)
                
            # Determine required rewind distance
            rewind_needed, rewind_point = self._calculate_rewind_needs(edit_operation)
            
            if rewind_needed:
                # Pause token generation
                await self.llm_client.pause_generation()
                
                # Rewind to safe point
                await self._rewind_to_checkpoint(rewind_point)
                
                # Apply the edit
                self.cursor.apply_edit(edit_operation)
                
                # Resume generation with modified context
                new_context = self.cursor.get_current_context()
                await self.llm_client.resume_generation(new_context)
            else:
                # Apply edit without rewind (future-only impact)
                self.cursor.apply_edit(edit_operation, future_only=True)