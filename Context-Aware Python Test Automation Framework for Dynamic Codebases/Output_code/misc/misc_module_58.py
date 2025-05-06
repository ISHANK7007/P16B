class RationaleDiff:
    """
    Captures the delta in rationale between standard constraint enforcement
    and the override decision, with detailed justification.
    """
    def __init__(self, original_rationale, override_rationale):
        self.original_rationale = original_rationale
        self.override_rationale = override_rationale
        self.delta_analysis = {}
        self.critical_factors = []
        self.supporting_evidence = []
        self.timestamp = time.time()
        
    def analyze_delta(self):
        """
        Analyze the difference between original and override rationales
        Identifies key points of divergence and reasoning changes
        """
        # Implementation would compare the rationales and identify
        # semantic differences, changes in priorities, etc.
        self.delta_analysis = self._compute_semantic_diff()
        self.critical_factors = self._identify_critical_factors()
        
    def add_supporting_evidence(self, evidence_type, content, source=None):
        """Add supporting evidence for the override decision"""
        self.supporting_evidence.append({
            "type": evidence_type,
            "content": content,
            "source": source,
            "timestamp": time.time()
        })
        
    def get_significance_score(self):
        """
        Calculate how significant the rationale change is
        Returns a score from 0.0 (minor) to 1.0 (major shift)
        """
        # Implementation would quantify the magnitude of the
        # rationale change based on semantic difference
        return self._calculate_semantic_distance()
        
    def to_dict(self):
        """Convert to dictionary for serialization"""
        return {
            "original_rationale": self.original_rationale,
            "override_rationale": self.override_rationale,
            "delta_analysis": self.delta_analysis,
            "critical_factors": self.critical_factors,
            "supporting_evidence": self.supporting_evidence,
            "significance_score": self.get_significance_score(),
            "timestamp": self.timestamp
        }
        
    def _compute_semantic_diff(self):
        """Compute semantic difference between rationales"""
        # Implementation would use NLP techniques to compare rationales
        pass
        
    def _identify_critical_factors(self):
        """Identify the most important factors in the rationale change"""
        # Implementation would extract key concepts and priorities
        pass
        
    def _calculate_semantic_distance(self):
        """Calculate the semantic distance between rationales"""
        # Implementation would compute vector similarity or other distance metric
        pass