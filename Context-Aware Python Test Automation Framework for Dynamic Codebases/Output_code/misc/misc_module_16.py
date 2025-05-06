class HierarchicalResolver:
    """
    Resolves conflicts based on role hierarchy and relationship rules
    """
    def __init__(self, role_hierarchy):
        self.role_hierarchy = role_hierarchy
        
    def resolve(self, conflict_group, context=None):
        """Resolve conflicts using role hierarchy"""
        if not conflict_group.proposals:
            return None
            
        # First try to find clear hierarchy winners
        by_role = {}
        for proposal in conflict_group.proposals:
            role = proposal.source_persona_role
            if role not in by_role:
                by_role[role] = []
            by_role[role].append(proposal)
            
        # Check for role-based overrides
        highest_priority = -1
        highest_role = None
        
        for role in by_role.keys():
            priority = self.role_hierarchy.get_priority(role)
            if priority > highest_priority:
                highest_priority = priority
                highest_role = role
                
        # If we have a clear winner by role, select best from that role
        if highest_role and by_role[highest_role]:
            candidates = by_role[highest_role]
            if len(candidates) == 1:
                return candidates[0]
            else:
                # If multiple from same role, select highest quality
                return max(candidates, key=lambda p: p.quality_score)
                
        # Fallback to quality score if no clear role priority
        return max(conflict_group.proposals, key=lambda p: p.quality_score)