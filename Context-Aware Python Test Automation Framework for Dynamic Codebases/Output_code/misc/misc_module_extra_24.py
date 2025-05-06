def calculate_entropy_metric(self) -> DivergenceMetric:
    """Calculate entropy-based divergence metric"""
    # Group decisions by their core decision hash
    decision_hashes = [d.generate_decision_hash() for d in self.decisions]
    counts = Counter(decision_hashes)
    
    # Calculate probabilities
    total = len(decision_hashes)
    probabilities = [count/total for count in counts.values()]
    
    # Calculate entropy using scipy
    entropy = scipy.stats.entropy(probabilities, base=2)
    
    # Normalize by max possible entropy
    max_entropy = np.log2(min(len(self.decisions), len(counts)))
    normalized_entropy = entropy / max_entropy if max_entropy > 0 else 0
    
    # Track individual contribution to entropy
    persona_contributions = {}
    for i, decision in enumerate(self.decisions):
        hash_key = decision_hashes[i]
        probability = counts[hash_key] / total
        information_content = -np.log2(probability)
        persona_contributions[decision.persona_id] = information_content
    
    return DivergenceMetric(
        type=DivergenceMetricType.ENTROPY,
        value=normalized_entropy,
        component_values=persona_contributions,
        explanation=f"Normalized entropy: {normalized_entropy:.3f} of maximum {max_entropy:.3f} bits."
    )