class RollbackGuard:
    """Prevents unsafe rollbacks that would create inconsistencies"""
    def __init__(self, protected_range, reason, criticality=1.0):
        self.start_idx = protected_range[0]
        self.end_idx = protected_range[1]
        self.reason = reason
        self.criticality = criticality  # How important this guard is (0-1)
        
    def conflicts_with_edit(self, edit_operation):
        """Check if an edit operation would conflict with this guard"""
        edit_start, edit_end = edit_operation.get_affected_range()
        
        # Check for overlap
        if max(self.start_idx, edit_start) <= min(self.end_idx, edit_end):
            return True, self.reason
            
        return False, None