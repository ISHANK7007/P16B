class StructuralCoherenceValidator:
    """Base class for validators checking structural integrity (quotes, code blocks, etc.)"""
    def __init__(self, structure_type):
        self.structure_type = structure_type
        
    def should_apply(self, tokens, metadata, tracking):
        """Determine if this validator should run on this window"""
        # Always check for structural issues
        return True
        
    def validate(self, tokens, metadata, tracking):
        """Validate structural coherence"""
        raise NotImplementedError("Subclasses must implement")
        

class QuoteBlockValidator(StructuralCoherenceValidator):
    """Validates that quote blocks are properly opened and closed"""
    def __init__(self):
        super().__init__("quote_block")
        
    def validate(self, tokens, metadata, tracking):
        text = "".join(tokens)
        
        # Track quote state
        open_quotes = text.count('\"')
        is_odd = open_quotes % 2 != 0
        
        # Check if we're in an ongoing quote
        in_quote = tracking.get("in_quote_block", False)
        
        if in_quote and not is_odd and "\"" in text:
            # Quote block closed
            return ValidationResult(
                is_valid=True,
                tracking_updates={"in_quote_block": False},
                message="Quote block properly closed"
            )
        elif not in_quote and is_odd:
            # New quote block started
            return ValidationResult(
                is_valid=True,
                tracking_updates={"in_quote_block": True},
                message="Quote block started"
            )
        elif in_quote and "\"" not in text and len(text) > 100:
            # Long text without closing quote
            return ValidationResult(
                is_valid=False,
                type="abandoned_quote",
                severity=0.8,
                location=len(tokens) - 10,
                message="Quote block has not been closed for over 100 characters",
                suggested_fix={
                    "type": "insert",
                    "content": "\"",
                    "position": len(tokens)
                }
            )
            
        return ValidationResult(is_valid=True)