class RuleFusionGraph:
    """
    Manages the hierarchical combination of constraint scores with override capabilities.
    Implements a directed acyclic graph for rule composition and precedence.
    """
    def __init__(self):
        self.weights = {
            "persona": 0.3,      # Default weight for persona constraints
            "formatting": 0.3,   # Default weight for formatting rules
            "bounds": 0.2,       # Default weight for boundary constraints
            "domain": 0.2        # Default weight for domain-specific rules
        }
        self.override_rules = [] # Special rules that can override normal weights
        self.fusion_strategy = "weighted_average"  # Default strategy
        
    def set_weights(self, weight_dict):
        """Update category weights"""
        self.weights.update(weight_dict)
        
    def add_override(self, rule, priority=1.0):
        """
        Add a rule that can override normal scoring
        Example: A safety constraint that must be satisfied
        """
        self.override_rules.append({"rule": rule, "priority": priority})
        self.override_rules.sort(key=lambda x: x["priority"], reverse=True)
        
    def resolve(self, score_dict, context=None):
        """
        Combine scores using the configured fusion strategy
        Applies overrides where appropriate
        """
        # First check if any override rules apply
        for override in self.override_rules:
            if override["rule"].applies(score_dict, context):
                return override["rule"].apply(score_dict, context)
        
        # If no overrides, use the standard fusion strategy
        if self.fusion_strategy == "weighted_average":
            return self._weighted_average(score_dict)
        elif self.fusion_strategy == "min_score":
            return self._minimum_score(score_dict)
        # Additional strategies can be implemented
        
    def _weighted_average(self, score_dict):
        """Combine scores using weighted average"""
        total = 0.0
        weight_sum = 0.0
        analysis = {}
        
        for category, scores in score_dict.items():
            if not scores:
                continue
                
            # Calculate category score (e.g., average of constraint scores)
            category_score = sum(s.value for s in scores) / len(scores)
            category_weight = self.weights.get(category, 0.1)
            
            total += category_score * category_weight
            weight_sum += category_weight
            analysis[category] = category_score
            
        # Normalize
        final_score = total / weight_sum if weight_sum > 0 else 0.5
        return FusionResult(value=final_score, analysis=analysis)