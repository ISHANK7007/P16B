class MemoryMappedTokenBuffer:
    """
    Uses memory-mapped files for token storage to reduce heap pressure
    while maintaining fast access for high-volume token streams.
    """
    def __init__(self, buffer_name, max_tokens=1000000):
        self.buffer_name = buffer_name
        self.max_tokens = max_tokens
        self.token_size = 64  # Average token size in bytes
        self.buffer_size = self.max_tokens * self.token_size
        
        # Create a temporary file for mapping
        self.file_path = f"/tmp/token_buffer_{buffer_name}.bin"
        self.file_handle = open(self.file_path, "w+b")
        self.file_handle.write(b'\0' * self.buffer_size)
        self.file_handle.flush()
        
        # Memory map the file
        self.mmap = mmap.mmap(
            self.file_handle.fileno(), 
            self.buffer_size,
            access=mmap.ACCESS_WRITE
        )
        
        # Token tracking
        self.token_count = 0
        self.index_map = {}  # Maps token IDs to positions
        
    def add_token(self, token):
        """Add a token to the buffer"""
        if self.token_count >= self.max_tokens:
            raise ValueError("Token buffer is full")
            
        # Serialize token
        token_data = json.dumps(token).encode('utf-8')
        token_len = len(token_data)
        
        if token_len > self.token_size:
            # Truncate or handle oversized tokens
            token_data = token_data[:self.token_size-4] + b'...'
            token_len = self.token_size
            
        # Write to mapped memory
        position = self.token_count * self.token_size
        self.mmap[position:position+token_len] = token_data.ljust(self.token_size, b'\0')
        
        # Update indices
        token_id = token.get('id', str(uuid.uuid4()))
        self.index_map[token_id] = self.token_count
        self.token_count += 1
        
        return token_id
        
    def get_token(self, token_id):
        """Get a token by ID"""
        if token_id not in self.index_map:
            return None
            
        index = self.index_map[token_id]
        position = index * self.token_size
        
        # Read data until null byte
        data = self.mmap[position:position+self.token_size].split(b'\0')[0]
        
        # Deserialize
        return json.loads(data)
        
    def get_tokens(self, start_idx, end_idx):
        """Get a range of tokens by index"""
        if start_idx < 0 or end_idx >= self.token_count:
            raise IndexError("Token index out of range")
            
        tokens = []
        for i in range(start_idx, end_idx + 1):
            position = i * self.token_size
            data = self.mmap[position:position+self.token_size].split(b'\0')[0]
            tokens.append(json.loads(data))
            
        return tokens
        
    def __del__(self):
        """Clean up resources"""
        if hasattr(self, 'mmap') and self.mmap:
            self.mmap.close()
            
        if hasattr(self, 'file_handle') and self.file_handle:
            self.file_handle.close()
            
        if hasattr(self, 'file_path') and os.path.exists(self.file_path):
            os.unlink(self.file_path)