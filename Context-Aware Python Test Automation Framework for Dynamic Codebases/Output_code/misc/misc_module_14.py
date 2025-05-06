class RoleHierarchy:
    """
    Defines the priority relationships between different roles
    """
    def __init__(self):
        # Higher priority roles take precedence in conflicts
        self.role_priorities = {
            "safety_monitor": 0.9,
            "fact_checker": 0.8,
            "domain_expert": 0.7,
            "editor": 0.6,
            "style_guide": 0.5,
            "creative": 0.4,
            "general": 0.3
        }
        
        # Define role dependencies/overrides
        self.role_relationships = {
            # Role: [roles it can override]
            "safety_monitor": ["creative", "style_guide", "editor", "general"],
            "fact_checker": ["creative", "general"],
            # ...
        }
        
    def get_priority(self, role):
        """Get the priority score for a role"""
        return self.role_priorities.get(role, 0.3)  # Default to general priority
        
    def can_override(self, role1, role2):
        """Check if role1 can override role2"""
        return role2 in self.role_relationships.get(role1, [])