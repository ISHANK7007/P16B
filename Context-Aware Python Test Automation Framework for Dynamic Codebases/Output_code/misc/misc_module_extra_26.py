def calculate_agreement_metric(self) -> DivergenceMetric:
    """Calculate agreement-based divergence metric"""
    # Count occurrences of each unique decision
    decision_hashes = [d.generate_decision_hash() for d in self.decisions]
    counts = Counter(decision_hashes)
    
    # Find the most common decision
    most_common_hash, most_common_count = counts.most_common(1)[0]
    
    # Calculate agreement rate
    agreement_rate = most_common_count / len(self.decisions)
    
    # Map personas to their agreement group
    persona_agreement = {
        d.persona_id: 1.0 if d.generate_decision_hash() == most_common_hash else 0.0
        for d in self.decisions
    }
    
    # Store decision clusters
    self.decision_clusters = []
    for hash_key, _ in counts.most_common():
        cluster = [
            d.persona_id for i, d in enumerate(self.decisions)
            if decision_hashes[i] == hash_key
        ]
        self.decision_clusters.append(cluster)
    
    return DivergenceMetric(
        type=DivergenceMetricType.DECISION_AGREEMENT,
        value=agreement_rate,
        component_values=persona_agreement,
        explanation=f"Agreement rate: {agreement_rate:.2f}."
    )