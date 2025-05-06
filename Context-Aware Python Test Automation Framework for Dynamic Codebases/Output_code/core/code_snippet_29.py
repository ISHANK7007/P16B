class CodeBlockValidator(StructuralCoherenceValidator):
    """Validates that code blocks are properly opened and closed"""
    def __init__(self):
        super().__init__("code_block")
        
    def validate(self, tokens, metadata, tracking):
        text = "".join(tokens)
        
        # Look for markdown code blocks
        code_block_starts = len(re.findall(r"```[a-zA-Z]*\n", text))
        code_block_ends = text.count("```\n")
        
        # Track state of code blocks
        in_code_block = tracking.get("in_code_block", False)
        
        if in_code_block and code_block_ends > code_block_starts:
            # Code block properly closed
            return ValidationResult(
                is_valid=True,
                tracking_updates={"in_code_block": False},
                message="Code block properly closed"
            )
        elif not in_code_block and code_block_starts > code_block_ends:
            # New code block started
            return ValidationResult(
                is_valid=True,
                tracking_updates={"in_code_block": True, 
                                 "code_block_language": self._extract_language(text)},
                message="Code block started"
            )
        elif in_code_block and code_block_starts == code_block_ends and len(text) > 200:
            # Long code block without closing
            return ValidationResult(
                is_valid=False,
                type="unclosed_code_block",
                severity=0.7,
                location=len(tokens) - 10,
                message="Code block has not been closed after significant content",
                suggested_fix={
                    "type": "insert",
                    "content": "```\n",
                    "position": len(tokens)
                }
            )
            
        return ValidationResult(is_valid=True)