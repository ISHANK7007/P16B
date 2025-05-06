class VotingMatrix:
    """
    Multi-criteria decision matrix for evaluating competing proposals
    """
    def __init__(self):
        self.matrix = {}  # {proposal_id: {criterion: (score, weight)}}
        
    def reset(self):
        """Clear the matrix for a new voting session"""
        self.matrix = {}
        
    def add_criterion_score(self, proposal_id, criterion, score, weight=1.0):
        """Add a score for a specific criterion to a proposal"""
        if proposal_id not in self.matrix:
            self.matrix[proposal_id] = {}
            
        self.matrix[proposal_id][criterion] = (score, weight)
        
    def get_score(self, proposal_id):
        """Calculate the weighted score for a proposal across all criteria"""
        if proposal_id not in self.matrix:
            return 0.0
            
        total_score = 0.0
        total_weight = 0.0
        
        for criterion, (score, weight) in self.matrix[proposal_id].items():
            total_score += score * weight
            total_weight += weight
            
        return total_score / total_weight if total_weight > 0 else 0.0
        
    def get_winner(self):
        """Return the proposal_id with the highest score"""
        if not self.matrix:
            return None
            
        return max(self.matrix.keys(), key=self.get_score)
        
    def get_all_scores(self):
        """Return all proposals with their scores, sorted by score"""
        scores = [(pid, self.get_score(pid)) for pid in self.matrix]
        return sorted(scores, key=lambda x: x[1], reverse=True)