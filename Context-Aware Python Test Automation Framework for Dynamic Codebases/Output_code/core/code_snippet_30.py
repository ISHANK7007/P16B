class InstructionFollowingValidator:
    """Validates that generated content follows the original instructions"""
    def __init__(self):
        self.instruction_patterns = [
            r"please (create|make|generate|write)",
            r"can you (create|make|generate|write)",
            r"i need (a|an|the)",
            r"provide (a|an|the)",
            r"write (a|an|the)"
        ]
        
    def should_apply(self, tokens, metadata, tracking):
        # Apply after sufficient context is available
        return len(tokens) >= 75
        
    def validate(self, tokens, metadata, tracking):
        text = "".join(tokens)
        
        # Extract instructions from tracking
        original_instructions = tracking.get("original_instructions")
        if not original_instructions:
            # Try to extract from the text
            instructions = self._extract_instructions(text)
            if not instructions:
                return ValidationResult(is_valid=True)
                
            tracking.update({"original_instructions": instructions})
            return ValidationResult(
                is_valid=True,
                tracking_updates={"original_instructions": instructions}
            )
            
        # Check if output aligns with instructions
        alignment_score = self._check_instruction_alignment(
            original_instructions, text)
            
        if alignment_score < 0.4:
            # Significant deviation from instructions
            return ValidationResult(
                is_valid=False,
                type="instruction_deviation",
                severity=0.8,
                message="Generated content deviates from original instructions",
                context={
                    "instructions": original_instructions,
                    "alignment_score": alignment_score
                }
            )
            
        return ValidationResult(is_valid=True)
        
    def _extract_instructions(self, text):
        """Extract instruction-like content from text"""
        for pattern in self.instruction_patterns:
            matches = re.findall(pattern + r"[^.!?]*[.!?]", text, re.IGNORECASE)
            if matches:
                return matches[0]
        return None