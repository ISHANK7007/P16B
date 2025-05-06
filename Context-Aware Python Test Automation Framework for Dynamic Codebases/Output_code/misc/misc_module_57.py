class PersonaDissent:
    """
    A record of a persona's dissent regarding a constraint override,
    including the specific objections and strength of dissent.
    """
    def __init__(self, persona_id, persona_role, dissent_score, objections=None, metadata=None):
        self.persona_id = persona_id
        self.persona_role = persona_role
        self.dissent_score = dissent_score  # 0.0 to 1.0
        self.objections = objections or []  # List of specific objections
        self.timestamp = time.time()
        self.session_id = None  # Will be set when registered
        self.persona_weight = 1.0  # Default weight, may be adjusted by role
        self.metadata = metadata or {}
        
    def add_objection(self, constraint_id, severity, reason):
        """Add a specific objection to this dissent"""
        self.objections.append({
            "constraint_id": constraint_id,
            "severity": severity,  # 0.0 to 1.0
            "reason": reason
        })
        
    def calculate_weight(self, role_hierarchy):
        """Calculate this dissent's weight based on role"""
        self.persona_weight = role_hierarchy.get_priority(self.persona_role)
        return self.persona_weight
        
    def to_dict(self):
        """Convert to dictionary for serialization"""
        return {
            "persona_id": self.persona_id,
            "persona_role": self.persona_role,
            "dissent_score": self.dissent_score,
            "objections": self.objections,
            "timestamp": self.timestamp,
            "session_id": self.session_id,
            "persona_weight": self.persona_weight,
            "metadata": self.metadata
        }