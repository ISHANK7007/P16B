class PromptFingerprint:
    """
    Generates and validates cryptographic fingerprints of prompts
    to detect tampering or corruption.
    """
    def __init__(self, hash_algorithm="sha256"):
        self.hash_algorithm = hash_algorithm
        self.salt = os.urandom(16)  # Random salt for fingerprinting
        
    def generate(self, prompt_text, metadata=None):
        """Generate a fingerprint for a prompt"""
        # Create a combined buffer of text and metadata
        buffer = prompt_text.encode('utf-8')
        
        # Add metadata if provided
        if metadata:
            metadata_str = json.dumps(metadata, sort_keys=True)
            buffer += metadata_str.encode('utf-8')
            
        # Add salt
        buffer += self.salt
        
        # Calculate hash
        hasher = hashlib.new(self.hash_algorithm)
        hasher.update(buffer)
        fingerprint = hasher.hexdigest()
        
        return {
            "fingerprint": fingerprint,
            "algorithm": self.hash_algorithm,
            "timestamp": time.time(),
            "metadata": metadata
        }
        
    def verify(self, prompt_text, stored_fingerprint, metadata=None):
        """Verify a prompt against a stored fingerprint"""
        # Calculate new fingerprint with same salt
        current_salt = self.salt
        self.salt = stored_fingerprint.get("salt", self.salt)
        
        try:
            new_fingerprint = self.generate(prompt_text, metadata)
            return new_fingerprint["fingerprint"] == stored_fingerprint["fingerprint"]
        finally:
            # Restore original salt
            self.salt = current_salt