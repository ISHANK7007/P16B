class ConstraintOverrideMutation:
    """
    A special mutation that can override constraints when necessary,
    with full transparency about the rationale and dissenting opinions.
    """
    def __init__(self, standard_mutation, override_reason, initiating_persona_id,
                override_priority=None, metadata=None):
        self.standard_mutation = standard_mutation  # The underlying mutation
        self.override_reason = override_reason  # Why constraints should be overridden
        self.initiating_persona = initiating_persona_id  # Who initiated the override
        self.override_priority = override_priority or 0.5  # Priority of this override
        self.metadata = metadata or {}
        self.dissent_reports = []  # Persona dissent reports
        self.rationale_diff = None  # Will be populated with rationale delta
        self.session_info = SessionContext()  # Captures session context
        self.applied_constraints = []  # Which constraints were satisfied
        self.overridden_constraints = []  # Which constraints were overridden
        
    def register_dissent(self, dissent_report):
        """Register a dissenting opinion about this override"""
        self.dissent_reports.append(dissent_report)
        
    def set_rationale_diff(self, rationale_diff):
        """Set the rationale difference analysis"""
        self.rationale_diff = rationale_diff
        
    def get_dissent_score(self):
        """Calculate the total dissent score"""
        if not self.dissent_reports:
            return 0.0
            
        # Sum weighted dissent scores
        total_weight = 0.0
        weighted_dissent = 0.0
        
        for report in self.dissent_reports:
            weight = report.persona_weight
            total_weight += weight
            weighted_dissent += report.dissent_score * weight
            
        # Normalize
        if total_weight > 0:
            return weighted_dissent / total_weight
        return 0.0
        
    def to_dict(self):
        """Convert to dictionary for serialization"""
        return {
            "mutation": self.standard_mutation.to_dict(),
            "override_reason": self.override_reason,
            "initiating_persona": self.initiating_persona,
            "override_priority": self.override_priority,
            "dissent_reports": [r.to_dict() for r in self.dissent_reports],
            "rationale_diff": self.rationale_diff.to_dict() if self.rationale_diff else None,
            "session_info": self.session_info.to_dict(),
            "applied_constraints": self.applied_constraints,
            "overridden_constraints": self.overridden_constraints,
            "metadata": self.metadata
        }