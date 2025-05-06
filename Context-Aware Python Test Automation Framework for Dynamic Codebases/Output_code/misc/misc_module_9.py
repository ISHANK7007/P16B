class OverrideRule:
    """Rule that can override standard fusion when conditions are met"""
    def applies(self, score_dict, context=None):
        """Determine if this override should be applied"""
        pass
        
    def apply(self, score_dict, context=None):
        """Apply special handling to the scores"""
        pass

class SafetyVeto(OverrideRule):
    """Immediately rejects mutations that violate safety constraints"""
    def applies(self, score_dict, context=None):
        safety_scores = context.get("safety_scores", [])
        return any(score.value < 0.2 for score in safety_scores)
        
    def apply(self, score_dict, context=None):
        return FusionResult(value=0.0, analysis={"override": "safety_violation"})