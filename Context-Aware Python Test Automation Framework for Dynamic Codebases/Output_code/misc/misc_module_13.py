class PersonaProfile:
    """
    Represents a persona or agent with its properties and metadata
    """
    def __init__(self, id, name, role, expertise=None):
        self.id = id
        self.name = name
        self.role = role  # e.g., "editor", "fact-checker", "safety_monitor"
        self.trust_score = 0.5  # Initial neutral trust score
        self.expertise = expertise or {}  # Domain-specific expertise levels
        self.mutation_history = []  # Track past mutations and outcomes
        self.preferences = {}  # Persona-specific preferences
        
    def update_trust(self, delta, reason=""):
        """Update trust score with bounds checking"""
        self.trust_score = max(0.0, min(1.0, self.trust_score + delta))
        self.mutation_history.append({
            "timestamp": time.time(),
            "trust_delta": delta,
            "reason": reason,
            "new_score": self.trust_score
        })
        
    def get_expertise(self, domain):
        """Get expertise level for a specific domain"""
        return self.expertise.get(domain, 0.1)  # Default low expertise