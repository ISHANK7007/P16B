class ConsensusResolver:
    """
    Attempts to merge compatible parts of competing proposals
    """
    def __init__(self, merger):
        self.mutation_merger = merger
        
    def resolve(self, conflict_group, context=None):
        """Try to build consensus by merging compatible proposals"""
        if len(conflict_group.proposals) <= 1:
            return conflict_group.proposals[0] if conflict_group.proposals else None
            
        # Sort proposals by quality score
        sorted_props = sorted(conflict_group.proposals, key=lambda p: p.quality_score, reverse=True)
        
        # Start with the highest quality proposal
        base_proposal = sorted_props[0]
        
        # Try to merge others where compatible
        for other_prop in sorted_props[1:]:
            if self.mutation_merger.can_merge(base_proposal, other_prop):
                base_proposal = self.mutation_merger.merge(base_proposal, other_prop)
                
        return base_proposal