class RingBufferedStreamChannel:
    """
    Memory-efficient stream buffer using a circular array to minimize allocations
    and support efficient lookback operations without copying.
    """
    def __init__(self, buffer_size=1024, agent_id=None):
        self.buffer_size = buffer_size
        self.buffer = [None] * buffer_size
        self.write_pointer = 0
        self.read_pointer = 0
        self.item_count = 0
        self.agent_id = agent_id
        self.metadata = {}
        self.overflow_count = 0
        
    def write(self, item):
        """Write an item to the buffer"""
        self.buffer[self.write_pointer] = item
        self.write_pointer = (self.write_pointer + 1) % self.buffer_size
        
        # Handle wrap-around and overflow
        if self.item_count == self.buffer_size:
            self.read_pointer = (self.read_pointer + 1) % self.buffer_size
            self.overflow_count += 1
        else:
            self.item_count += 1
        
        return self.write_pointer - 1
        
    def read(self, count=None, offset=0):
        """Read items from the buffer without removing them"""
        if count is None:
            count = self.item_count
            
        if count > self.item_count:
            count = self.item_count
            
        result = []
        read_pos = (self.read_pointer + offset) % self.buffer_size
        
        for i in range(count):
            result.append(self.buffer[read_pos])
            read_pos = (read_pos + 1) % self.buffer_size
            
        return result
        
    def get_window(self, start_idx, end_idx):
        """Get a sliding window of items by logical index"""
        # Convert logical indices to buffer indices
        if self.overflow_count > 0:
            # Adjust for overflow
            oldest_logical_idx = self.overflow_count
            
            if start_idx < oldest_logical_idx:
                # Some items are no longer available
                start_idx = oldest_logical_idx
                
        if start_idx > end_idx or start_idx >= self.overflow_count + self.item_count:
            return []
            
        buf_start = (self.read_pointer + (start_idx - self.overflow_count)) % self.buffer_size
        buf_end = (self.read_pointer + (end_idx - self.overflow_count)) % self.buffer_size
        
        result = []
        pos = buf_start
        
        while pos != buf_end:
            result.append(self.buffer[pos])
            pos = (pos + 1) % self.buffer_size
            
        # Include the last item
        if end_idx < self.overflow_count + self.item_count:
            result.append(self.buffer[buf_end])
            
        return result