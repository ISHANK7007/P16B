class OverrideDecision:
    """
    Records a decision about a constraint override, including
    rationale and contributing factors.
    """
    def __init__(self, mutation_id, session_id, initiating_persona):
        self.mutation_id = mutation_id
        self.session_id = session_id
        self.initiating_persona = initiating_persona
        self.timestamp = time.time()
        self.allowed = False
        self.dissent_score = 0.0
        self.threshold = 0.0
        self.constraint_analysis = {}
        self.rationale = ""
        
    def set_rationale(self, rationale):
        """Set the decision rationale"""
        self.rationale = rationale
        
    def to_dict(self):
        """Convert to dictionary for serialization"""
        return {
            "mutation_id": self.mutation_id,
            "session_id": self.session_id,
            "initiating_persona": self.initiating_persona,
            "timestamp": self.timestamp,
            "allowed": self.allowed,
            "dissent_score": self.dissent_score,
            "threshold": self.threshold,
            "constraint_analysis": self.constraint_analysis,
            "rationale": self.rationale
        }