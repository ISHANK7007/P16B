class SpanMetadata:
    """
    Metadata and lineage information for a text span
    """
    def __init__(self, id, text, start_pos, end_pos, turn_id, creation_timestamp,
                parent_id=None, mutation_id=None, operation_type=None, metadata=None):
        self.id = id  # Fingerprint ID
        self.text = text  # The actual text content
        self.start_pos = start_pos  # Start position in the prompt
        self.end_pos = end_pos  # End position in the prompt
        self.turn_id = turn_id  # Dialogue turn ID when this span was created
        self.creation_timestamp = creation_timestamp
        self.parent_id = parent_id  # ID of the span this was derived from
        self.mutation_id = mutation_id  # ID of the mutation that created this span
        self.operation_type = operation_type  # Type of operation (insert, replace, delete)
        self.metadata = metadata or {}  # Additional metadata
        
    def to_dict(self):
        """Convert to dictionary for serialization"""
        return {
            "id": self.id,
            "text": self.text,
            "position": [self.start_pos, self.end_pos],
            "turn_id": self.turn_id,
            "parent_id": self.parent_id,
            "mutation_id": self.mutation_id,
            "operation": self.operation_type,
            "creation_time": self.creation_timestamp,
            "metadata": self.metadata
        }