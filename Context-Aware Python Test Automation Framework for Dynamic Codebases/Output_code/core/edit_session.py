class EditSession:
    """Represents an active editing session with applied patches"""
    def __init__(self, prompt_template, constraints=None):
        self.id = str(uuid.uuid4())
        self.prompt_template = prompt_template
        self.constraints = constraints or []
        self.patches = []  # Applied edit patches
        self.token_stream = TokenStream()  # Tracks streaming tokens
        
    def add_patch(self, patch):
        """Add a patch overlay to the session"""
        self.patches.append(patch)
        
    def get_effective_prompt(self):
        """Get current prompt with all patches applied"""
        result = self.prompt_template
        for patch in sorted(self.patches, key=lambda p: p.timestamp):
            result = patch.apply_to(result)
        return result