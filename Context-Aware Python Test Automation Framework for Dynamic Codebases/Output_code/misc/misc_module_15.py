class ConflictGroup:
    """
    A group of competing mutation proposals that affect overlapping regions
    """
    def __init__(self):
        self.proposals = []  # List of MutationProposal objects
        self.region = None  # Affected prompt region
        
    def add_proposal(self, proposal):
        self.proposals.append(proposal)
        
    def get_proposal_by_id(self, proposal_id):
        for p in self.proposals:
            if p.id == proposal_id:
                return p
        return None