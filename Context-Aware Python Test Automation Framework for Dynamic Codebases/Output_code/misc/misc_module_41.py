class ConflictRegion:
    """
    Represents a group of conflicting mutation proposals
    that must be evaluated together
    """
    def __init__(self):
        self.id = str(uuid.uuid4())
        self.proposals = []  # List of mutation proposals
        self.bounding_box = None  # TextRegion encompassing all mutations
        self.interested_agents = []  # Agents with a stake in this region
        self.metadata = {}  # Additional metadata
        
    def add_proposal(self, proposal):
        """Add a proposal to this conflict region"""
        self.proposals.append(proposal)
        self._update_bounding_box(proposal)
        
    def _update_bounding_box(self, proposal):
        """Update the bounding box to include the proposal's regions"""
        for region in proposal.affected_regions:
            if not self.bounding_box:
                self.bounding_box = TextRegion(region.start, region.end)
            else:
                # Expand bounding box
                self.bounding_box.start = min(self.bounding_box.start, region.start)
                self.bounding_box.end = max(self.bounding_box.end, region.end)
                
    def get_complexity_score(self):
        """
        Calculate the computational complexity of evaluating this region
        Used for scheduling and optimization
        """
        # Simple implementation: score based on number of proposals and region size
        proposal_count = len(self.proposals)
        region_size = self.bounding_box.end - self.bounding_box.start if self.bounding_box else 0
        
        return proposal_count * region_size