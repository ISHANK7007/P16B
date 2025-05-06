class OverrideDecisionEngine:
    """
    Makes decisions about whether to allow constraint overrides
    based on rationale, dissent, and session context.
    """
    def __init__(self, dissent_registry=None, role_hierarchy=None):
        self.dissent_registry = dissent_registry or DissentRegistry()
        self.role_hierarchy = role_hierarchy or RoleHierarchy()
        self.override_thresholds = {
            "default": 0.7,  # Default threshold for allowing override
            "critical": 0.9,  # Threshold for critical constraints
            "safety": 0.95,  # Threshold for safety constraints
        }
        self.decision_history = []
        
    def evaluate_override(self, override_mutation, constraint_results, session_context):
        """
        Evaluate whether to allow a constraint override
        Returns a decision with detailed rationale
        """
        # Create the decision object
        decision = OverrideDecision(
            mutation_id=override_mutation.standard_mutation.id,
            session_id=session_context.session_id,
            initiating_persona=override_mutation.initiating_persona
        )
        
        # Get dissent reports with decay applied
        dissent_reports = self.dissent_registry.get_dissent_reports(
            override_mutation.standard_mutation.id,
            apply_decay=True,
            session_context=session_context
        )
        
        # Calculate weighted dissent score
        dissent_score = self._calculate_weighted_dissent(dissent_reports)
        decision.dissent_score = dissent_score
        
        # Analyze constraint results
        constraint_analysis = self._analyze_constraints(constraint_results)
        decision.constraint_analysis = constraint_analysis
        
        # Add failed constraints to the mutation record
        override_mutation.applied_constraints = constraint_analysis["passed"]
        override_mutation.overridden_constraints = constraint_analysis["failed"]
        
        # Get threshold based on constraint types
        threshold = self._determine_threshold(constraint_analysis)
        decision.threshold = threshold
        
        # Check if override should be allowed
        override_priority = override_mutation.override_priority
        adjusted_priority = self._adjust_priority_by_role(
            override_priority,
            override_mutation.initiating_persona,
            self.role_hierarchy
        )
        
        # Decision formula: priority must exceed threshold + dissent
        allow_override = adjusted_priority > (threshold + dissent_score)
        decision.allowed = allow_override
        
        # Record the decision
        self.decision_history.append(decision)
        
        return decision
        
    def _calculate_weighted_dissent(self, dissent_reports):
        """Calculate weighted dissent score from reports"""
        if not dissent_reports:
            return 0.0
            
        total_weight = 0.0
        weighted_sum = 0.0
        
        for report in dissent_reports:
            weight = report.persona_weight
            total_weight += weight
            weighted_sum += report.dissent_score * weight
            
        if total_weight > 0:
            return weighted_sum / total_weight
        return 0.0
        
    def _analyze_constraints(self, constraint_results):
        """Analyze which constraints passed and failed"""
        analysis = {
            "passed": [],
            "failed": [],
            "by_category": {},
            "critical_failed": False
        }
        
        for constraint_id, result in constraint_results.items():
            if result.get("passed", False):
                analysis["passed"].append(constraint_id)
            else:
                analysis["failed"].append(constraint_id)
                
                # Check constraint category
                category = result.get("category", "default")
                if category not in analysis["by_category"]:
                    analysis["by_category"][category] = {"passed": [], "failed": []}
                if result.get("passed", False):
                    analysis["by_category"][category]["passed"].append(constraint_id)
                else:
                    analysis["by_category"][category]["failed"].append(constraint_id)
                    
                # Check if critical constraints failed
                if result.get("critical", False):
                    analysis["critical_failed"] = True
                    
        return analysis
        
    def _determine_threshold(self, constraint_analysis):
        """Determine the override threshold based on constraint types"""
        # Start with default threshold
        threshold = self.override_thresholds["default"]
        
        # Check for critical constraints
        if constraint_analysis["critical_failed"]:
            threshold = max(threshold, self.override_thresholds["critical"])
            
        # Check for safety constraints
        if "safety" in constraint_analysis["by_category"] and \
           constraint_analysis["by_category"]["safety"]["failed"]:
               threshold = max(threshold, self.override_thresholds["safety"])
               
        return threshold
        
    def _adjust_priority_by_role(self, priority, persona_id, role_hierarchy):
        """Adjust override priority based on persona role"""
        # Implementation would adjust priority based on role
        # Higher priority roles get a boost
        pass