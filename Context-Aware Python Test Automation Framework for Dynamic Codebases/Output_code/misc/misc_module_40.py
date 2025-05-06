class SpatialIndex:
    """
    Efficient spatial index for quickly finding overlapping text regions
    """
    def __init__(self):
        self.regions = []  # List of (start, end, id) tuples
        
    def insert(self, region, region_id):
        """Insert a region into the index"""
        self.regions.append((region.start, region.end, region_id))
        
    def query_overlapping(self, query_region):
        """Find all regions that overlap with the query region"""
        results = []
        query_start, query_end = query_region.start, query_region.end
        
        for start, end, region_id in self.regions:
            # Check for overlap
            if max(start, query_start) <= min(end, query_end):
                results.append(region_id)
                
        return results
        
    def clear(self):
        """Clear the index"""
        self.regions = []