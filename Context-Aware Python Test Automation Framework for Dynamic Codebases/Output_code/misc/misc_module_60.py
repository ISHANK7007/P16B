class DissentDecayManager:
    """
    Manages the decay of dissent weights across session hops
    with configurable decay functions.
    """
    def __init__(self, default_decay_function="exponential", default_half_life=3):
        self.decay_functions = {
            "exponential": self._exponential_decay,
            "linear": self._linear_decay,
            "step": self._step_decay,
            "sigmoid": self._sigmoid_decay
        }
        self.default_decay_function = default_decay_function
        self.default_half_life = default_half_life
        self.role_decay_config = {}  # Custom decay config by role
        self.persistence_thresholds = {}  # Min threshold by role
        
    def configure_role_decay(self, role, decay_function, half_life=None, persistence_threshold=0.1):
        """Configure decay parameters for a specific role"""
        if decay_function not in self.decay_functions:
            raise ValueError(f"Unknown decay function: {decay_function}")
            
        self.role_decay_config[role] = {
            "function": decay_function,
            "half_life": half_life or self.default_half_life,
            "persistence_threshold": persistence_threshold
        }
        self.persistence_thresholds[role] = persistence_threshold
        
    def calculate_decay_factor(self, dissent_report, session_context):
        """
        Calculate the decay factor for a dissent report 
        based on session hops and role configuration
        """
        role = dissent_report.persona_role
        hops = session_context.session_depth
        
        if hops == 0:
            return 1.0  # No decay for current session
            
        # Get role-specific config or use defaults
        config = self.role_decay_config.get(role, {
            "function": self.default_decay_function,
            "half_life": self.default_half_life,
            "persistence_threshold": 0.1
        })
        
        # Calculate decay using the specified function
        decay_func = self.decay_functions[config["function"]]
        decay_factor = decay_func(hops, config["half_life"])
        
        # Ensure we don't decay below the persistence threshold
        return max(decay_factor, config["persistence_threshold"])
        
    def apply_decay(self, dissent_reports, session_context):
        """
        Apply decay to a list of dissent reports based on session context
        Returns updated reports with decayed weights
        """
        if session_context.session_depth == 0:
            return dissent_reports  # No decay needed for current session
            
        updated_reports = []
        
        for report in dissent_reports:
            # Clone the report to avoid modifying the original
            updated = copy.deepcopy(report)
            
            # Calculate and apply decay factor
            decay_factor = self.calculate_decay_factor(report, session_context)
            updated.persona_weight *= decay_factor
            
            updated_reports.append(updated)
            
        return updated_reports
        
    def _exponential_decay(self, hops, half_life):
        """Exponential decay function"""
        return 0.5 ** (hops / half_life)
        
    def _linear_decay(self, hops, max_hops):
        """Linear decay function"""
        return max(0, 1 - (hops / max_hops))
        
    def _step_decay(self, hops, step_size):
        """Step decay function"""
        return 0.5 ** (hops // step_size)
        
    def _sigmoid_decay(self, hops, mid_point):
        """Sigmoid decay function for smoother transition"""
        return 1 / (1 + math.exp(0.5 * (hops - mid_point)))