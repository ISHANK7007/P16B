class AuditEnabledPersonaArbiter(PersonaArbiter):
    def __init__(self, personas, audit_trace_provider=None):
        super().__init__(personas)
        self.audit_trace_provider = audit_trace_provider
        
    def arbitrate(self, mutations, format):
        """Arbitrate with audit trail generation"""
        # Record pre-arbitration state
        current_trace = self._get_current_trace()
        if current_trace:
            self._record_arbitration_event(current_trace, "arbitration_started", {
                "mutation_count": len(mutations),
                "format": format.name
            })
        
        # Perform regular arbitration
        selected = super().arbitrate(mutations, format)
        
        # Record decision and rationale
        if current_trace:
            self._record_arbitration_event(current_trace, "arbitration_completed", {
                "selected_mutation_index": mutations.index(selected),
                "decision_rationale": "Selected based on expertise match" if format in [PromptFormat.JSON, PromptFormat.SQL] else "Default selection"
            })
            
        return selected