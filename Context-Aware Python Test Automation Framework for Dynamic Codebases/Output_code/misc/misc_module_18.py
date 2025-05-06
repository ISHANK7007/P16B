class MutationProposal:
    """
    A proposed mutation to a prompt, with metadata about source and quality
    """
    def __init__(self, mutation, source_persona, source_persona_role, metadata=None):
        self.id = str(uuid.uuid4())
        self.mutation = mutation  # The actual mutation object
        self.source_persona = source_persona  # ID of proposing persona
        self.source_persona_role = source_persona_role  # Role of proposing persona
        self.timestamp = time.time()
        self.quality_score = 0.5  # Initial quality estimate
        self.context_alignment_score = 0.5  # How well it aligns with context
        self.metadata = metadata or {}  # Additional metadata
        
    def affects_region(self, start_idx, end_idx):
        """Check if this mutation affects the given region"""
        return self.mutation.overlaps_with(start_idx, end_idx)
        
    def to_dict(self):
        """Convert to dictionary for serialization"""
        return {
            "id": self.id,
            "source_persona": self.source_persona,
            "source_role": self.source_persona_role,
            "timestamp": self.timestamp,
            "quality_score": self.quality_score,
            "context_alignment": self.context_alignment_score,
            "mutation": self.mutation.to_dict(),
            "metadata": self.metadata
        }