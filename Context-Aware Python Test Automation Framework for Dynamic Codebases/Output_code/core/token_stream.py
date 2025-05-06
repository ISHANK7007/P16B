class TokenStream:
    """Manages the token stream with edit overlay capabilities"""
    def __init__(self):
        self.tokens = []
        self.anchors = {}  # Key points in the stream for targeting edits
        
    def add_token(self, token, metadata=None):
        """Add new token to the stream with optional anchoring metadata"""
        token_idx = len(self.tokens)
        self.tokens.append(token)
        
        if metadata and metadata.get('is_anchor'):
            self.anchors[metadata['anchor_name']] = token_idx
            
        return token_idx
        
    def apply_constraint(self, constraint, anchor_point=None):
        """Apply a constraint injection at a specific anchor point"""
        target_idx = len(self.tokens) if anchor_point is None else self.anchors.get(anchor_point)
        if target_idx is None:
            # Fallback to token matching if anchor not found
            target_idx = self._find_best_match(constraint.context_pattern)
            
        return target_idx