class PolicyConflictDetector:
    """Detects conflicts between routing policies"""
    
    def __init__(self, trace_manager: RoutingTraceManager):
        self.trace_manager = trace_manager
        self.policy_applications = {}  # service -> policy -> count
        self.policy_overlaps = {}  # (policy1, policy2) -> count
        
    def analyze_policy_application(self, trace: RoutingTrace) -> Dict:
        """Analyze policy application and detect conflicts"""
        service = trace.service
        
        # Get all policy evaluations
        policy_decisions = [d for d in trace.decision_points 
                         if d.decision_type == DecisionType.POLICY_EVALUATION]
        
        # Get all stakeholder selections
        stakeholder_decisions = [d for d in trace.decision_points
                              if d.decision_type == DecisionType.STAKEHOLDER_SELECTION]
        
        # Update counters
        if service not in self.policy_applications:
            self.policy_applications[service] = {}
            
        for decision in policy_decisions:
            policy_name = decision.rule_name
            if policy_name not in self.policy_applications[service]:
                self.policy_applications[service][policy_name] = 0
            self.policy_applications[service][policy_name] += 1
            
        # Check for overlaps in stakeholder selection
        all_stakeholders = set()
        stakeholder_by_policy = {}
        
        for decision in stakeholder_decisions:
            stakeholders = set(decision.output_state.get("stakeholders", []))
            policy_name = decision.rule_name
            stakeholder_by_policy[policy_name] = stakeholders
            
            # Check for overlap with already seen stakeholders
            overlap = stakeholders & all_stakeholders
            if overlap:
                # There's an overlap - potential conflict
                for other_policy, other_stakeholders in stakeholder_by_policy.items():
                    if policy_name != other_policy:
                        shared = stakeholders & other_stakeholders
                        if shared:
                            # Record this overlap
                            key = tuple(sorted([policy_name, other_policy]))
                            if key not in self.policy_overlaps:
                                self.policy_overlaps[key] = 0
                            self.policy_overlaps[key] += 1
                            
            # Add to all stakeholders set
            all_stakeholders.update(stakeholders)
            
        # Check for conflicts based on history
        conflicts = []
        if service in self.policy_applications:
            # Policies that frequently overlap might be conflicting
            for (p1, p2), count in self.policy_overlaps.items():
                if count > 10:  # Arbitrary threshold
                    conflicts.append({
                        "policies": [p1, p2],
                        "overlap_count": count,
                        "overlap_percentage": count / max(self.policy_applications[service].get(p1, 0),
                                                        self.policy_applications[service].get(p2, 0)),
                    })
                    
        return {
            "service": service,
            "policy_applications": self.policy_applications.get(service, {}),
            "conflicts": conflicts
        }