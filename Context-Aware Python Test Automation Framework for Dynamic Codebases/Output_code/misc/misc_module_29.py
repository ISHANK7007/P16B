class EnhancedMutationProposal(MutationProposal):
    """
    Enhanced mutation proposal with span tracking and fingerprinting
    """
    def __init__(self, mutation, source_persona, source_persona_role, metadata=None):
        super().__init__(mutation, source_persona, source_persona_role, metadata)
        self.affected_spans = []  # List of span IDs affected by this mutation
        self.created_spans = []  # List of span IDs created by this mutation
        self.span_operations = []  # List of operations performed on spans
        
    def register_span_operation(self, operation_type, original_span_id, new_span_id=None):
        """Register an operation performed on a span"""
        self.span_operations.append({
            "operation": operation_type,
            "original_span_id": original_span_id,
            "new_span_id": new_span_id,
            "timestamp": time.time()
        })
        
        if original_span_id and original_span_id not in self.affected_spans:
            self.affected_spans.append(original_span_id)
            
        if new_span_id and new_span_id not in self.created_spans:
            self.created_spans.append(new_span_id)