class TextRegion:
    """
    Represents a contiguous region of text in the prompt
    """
    def __init__(self, start, end, metadata=None):
        self.start = start  # Start index (inclusive)
        self.end = end  # End index (exclusive)
        self.metadata = metadata or {}
        
    def overlaps_with(self, other):
        """Check if this region overlaps with another"""
        return max(self.start, other.start) < min(self.end, other.end)
        
    def contains(self, other):
        """Check if this region fully contains another"""
        return self.start <= other.start and self.end >= other.end
        
    def size(self):
        """Get the size of this region in characters"""
        return self.end - self.start