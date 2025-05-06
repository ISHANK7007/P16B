class SemanticAlignmentWindow:
    """Tracks semantic relationships between prompt edits and generated tokens"""
    def __init__(self, start_position, window_size):
        self.start_position = start_position
        self.window_size = window_size
        self.token_relationships = {}  # Maps tokens to semantic concepts
        self.concept_strengths = {}    # Tracks semantic importance
        
    def add_token_relationship(self, token_idx, concept, strength):
        """Associate a token with a semantic concept at a certain strength"""
        if token_idx not in self.token_relationships:
            self.token_relationships[token_idx] = []
        self.token_relationships[token_idx].append((concept, strength))
        
        # Update concept importance
        current = self.concept_strengths.get(concept, 0.0)
        self.concept_strengths[concept] = max(current, strength)
        
    def get_affected_concepts(self, start_idx, end_idx):
        """Return concepts affected if tokens in range were changed"""
        affected = {}
        for idx in range(start_idx, end_idx + 1):
            if idx in self.token_relationships:
                for concept, strength in self.token_relationships[idx]:
                    affected[concept] = max(affected.get(concept, 0.0), strength)
        return affected