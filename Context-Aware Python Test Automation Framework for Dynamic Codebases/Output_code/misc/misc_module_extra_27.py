def calculate_constraint_violation_metric(self) -> DivergenceMetric:
    """Calculate constraint violation divergence metric"""
    # Collect all constraint keys
    all_constraints = set()
    for decision in self.decisions:
        all_constraints.update(decision.constraint_scores.keys())
    
    # For each constraint, calculate variance in scores
    constraint_variances = {}
    for constraint in all_constraints:
        scores = [
            d.constraint_scores.get(constraint, 0.0) 
            for d in self.decisions 
            if constraint in d.constraint_scores
        ]
        
        if scores:
            constraint_variances[constraint] = np.var(scores)
    
    # Average variance across all constraints
    avg_variance = np.mean(list(constraint_variances.values())) if constraint_variances else 0.0
    
    return DivergenceMetric(
        type=DivergenceMetricType.CONSTRAINT_VIOLATION,
        value=avg_variance,
        component_values=constraint_variances,
        explanation=f"Average constraint score variance: {avg_variance:.3f}."
    )