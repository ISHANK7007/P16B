def calculate_vector_distance_metric(self) -> DivergenceMetric:
    """Calculate vector distance-based divergence metric"""
    # Filter decisions with vectors
    decisions_with_vectors = [d for d in self.decisions if d.rationale_vector is not None]
    
    # Calculate pairwise distances using cosine similarity
    vectors = np.array([d.rationale_vector for d in decisions_with_vectors])
    similarities = cosine_similarity(vectors)
    distances = 1 - similarities
    
    # Calculate maximum and average distances
    max_distance = np.max(distances)
    avg_distance = np.mean(distances)
    
    # Calculate distances between each persona and the centroid
    centroid = np.mean(vectors, axis=0)
    centroid_distances = {
        d.persona_id: 1 - cosine_similarity(
            np.array([d.rationale_vector]), np.array([centroid])
        )[0][0]
        for d in decisions_with_vectors
    }
    
    return DivergenceMetric(
        type=DivergenceMetricType.VECTOR_DISTANCE,
        value=max_distance,
        component_values=centroid_distances,
        explanation=f"Maximum vector distance: {max_distance:.3f}, Average: {avg_distance:.3f}"
    )