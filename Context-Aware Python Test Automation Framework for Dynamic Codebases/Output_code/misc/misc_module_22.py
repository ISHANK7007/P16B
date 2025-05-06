class Agent:
    """
    An autonomous agent that can propose prompt mutations based on its expertise
    """
    def __init__(self, id, persona_id, role, mutation_generator):
        self.id = id
        self.persona_id = persona_id
        self.role = role
        self.mutation_generator = mutation_generator
        self.confidence_estimator = None  # Optional confidence estimation module
        
    def generate_mutations(self, prompt, context=None, max_proposals=3):
        """Generate mutation proposals based on agent's role and expertise"""
        # Implementation would generate role-specific mutations
        # For example:
        if self.role == "safety_monitor":
            return self._generate_safety_mutations(prompt, context)
        elif self.role == "fact_checker":
            return self._generate_factual_mutations(prompt, context)
        else:
            return self.mutation_generator.generate(prompt, context, max_proposals)
            
    def has_domain_expertise(self, domain):
        """Check if agent has expertise in a specific domain"""
        # Implementation would check the agent's capabilities
        return domain in self.domains_of_expertise
        
    def get_confidence(self, mutation):
        """Estimate confidence in a generated mutation"""
        if self.confidence_estimator:
            return self.confidence_estimator.estimate(mutation, self.role)
        return 0.7  # Default medium-high confidence