class MemoryEfficientDiffStore:
    """
    Optimized storage for diffs using reference counting and shared segments
    to minimize memory consumption for overlapping edits.
    """
    def __init__(self):
        self.diff_registry = {}
        self.shared_segments = {}
        self.reference_counts = {}
        
    def store_diff(self, diff):
        """Store a diff with memory optimization"""
        # Register the diff
        diff_id = diff.id
        self.diff_registry[diff_id] = {
            "metadata": diff.metadata,
            "segments": []
        }
        
        # Process each segment
        for segment in diff.segments:
            # Check if segment can be shared
            segment_hash = self._compute_segment_hash(segment)
            
            if segment_hash in self.shared_segments:
                # Reuse existing segment
                segment_id = self.shared_segments[segment_hash]
                self.reference_counts[segment_id] += 1
            else:
                # Store new segment
                segment_id = str(uuid.uuid4())
                self.shared_segments[segment_hash] = segment_id
                self._store_segment(segment_id, segment)
                self.reference_counts[segment_id] = 1
                
            # Add segment reference to diff
            self.diff_registry[diff_id]["segments"].append({
                "segment_id": segment_id,
                "offset": segment.offset,
                "operation_type": segment.operation_type
            })
            
        return diff_id
        
    def retrieve_diff(self, diff_id):
        """Retrieve a complete diff by reconstructing from segments"""
        if diff_id not in self.diff_registry:
            return None
            
        diff_data = self.diff_registry[diff_id]
        segments = []
        
        for segment_ref in diff_data["segments"]:
            segment_content = self._retrieve_segment(segment_ref["segment_id"])
            segments.append(DiffSegment(
                content=segment_content,
                offset=segment_ref["offset"],
                operation_type=segment_ref["operation_type"]
            ))
            
        return Diff(
            id=diff_id,
            segments=segments,
            metadata=diff_data["metadata"]
        )
        
    def _compute_segment_hash(self, segment):
        """Compute a hash for segment content to identify duplicates"""
        return hashlib.md5(
            f"{segment.content}:{segment.operation_type}".encode()
        ).hexdigest()