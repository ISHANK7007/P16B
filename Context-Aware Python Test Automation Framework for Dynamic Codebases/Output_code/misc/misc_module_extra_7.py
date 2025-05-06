class EnhancedMutationEngine(MutationEngine):
    def __init__(self, constraint_manager, history_limit=100, audit_enabled=True):
        super().__init__(constraint_manager, history_limit)
        self.audit_enabled = audit_enabled
        self.current_audit_trace = None
        self.audit_repository = AuditTraceRepository()
        
    def start_mutation_session(self, prompt_id, format):
        """Start a new mutation session with audit tracking"""
        self.current_audit_trace = MutationAuditTrace(
            session_id=f"{prompt_id}-{uuid.uuid4()}",
            start_time=datetime.datetime.now(),
            prompt_format=format
        )
        
    def mutate(self, prompt, format, target_model_capabilities=None, personas=None):
        """Enhanced mutation with audit trail"""
        # Record pre-mutation state
        if self.audit_enabled and self.current_audit_trace:
            self._record_audit_event("mutation_started", {
                "original_prompt": prompt,
                "format": format.name,
                "capabilities": [c.name for c in (target_model_capabilities or [])]
            })
            
        # Perform mutation (parent implementation)
        mutation = super().mutate(prompt, format, target_model_capabilities, personas)
        
        # Record post-mutation state
        if self.audit_enabled and self.current_audit_trace:
            self._record_audit_event("mutation_completed", {
                "mutated_prompt": mutation.mutated,
                "rationale": mutation.mutation_rationale
            })
            
        return mutation
        
    def _record_audit_event(self, event_type, details, persona=None, severity=1):
        """Record an audit event in the current trace"""
        if not self.current_audit_trace:
            return
            
        event = MutationAuditEvent(
            timestamp=datetime.datetime.now(),
            event_type=event_type,
            component="MutationEngine",
            prompt_id=self.current_audit_trace.session_id.split('-')[0],
            details=details,
            persona=persona,
            severity=severity
        )
        
        self.current_audit_trace.events.append(event)