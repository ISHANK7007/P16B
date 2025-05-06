class InstructionDriftValidator:
    """Detects instruction drift where generation diverges from original prompt intent"""
    def __init__(self, drift_threshold=0.6):
        self.drift_threshold = drift_threshold
        self.embedding_cache = {}
        
    def should_apply(self, tokens, metadata, tracking):
        # Apply periodically on larger chunks
        return len(tokens) >= 50
        
    def validate(self, tokens, metadata, tracking):
        if "original_intent_embedding" not in tracking:
            # Can't validate drift without original intent
            return ValidationResult(is_valid=True)
            
        # Get embedding for current window
        current_text = "".join(tokens)
        current_embedding = self._get_embedding(current_text)
        
        # Calculate drift score (distance from original intent)
        original_embedding = tracking["original_intent_embedding"]
        drift_score = self._calculate_semantic_distance(
            original_embedding, current_embedding)
            
        if drift_score > self.drift_threshold:
            return ValidationResult(
                is_valid=False,
                type="instruction_drift",
                severity=min(1.0, drift_score),
                message=f"Generation has drifted from original intent (score: {drift_score:.2f})",
                context={
                    "drift_score": drift_score,
                    "original_intent": tracking.get("original_intent_text", "Unknown"),
                    "current_text": current_text[:100] + "..." if len(current_text) > 100 else current_text
                }
            )
            
        return ValidationResult(is_valid=True)
        
    def _get_embedding(self, text):
        """Get semantic embedding for text (with caching)"""
        if text in self.embedding_cache:
            return self.embedding_cache[text]
            
        # In a real implementation, this would call an embedding model
        # For now, we'll use a placeholder
        embedding = [0.1] * 10  # Placeholder
        self.embedding_cache[text] = embedding
        return embedding
        
    def _calculate_semantic_distance(self, embedding1, embedding2):
        """Calculate semantic distance between embeddings"""
        # Simple Euclidean distance for example
        return sum((a - b) ** 2 for a, b in zip(embedding1, embedding2)) ** 0.5