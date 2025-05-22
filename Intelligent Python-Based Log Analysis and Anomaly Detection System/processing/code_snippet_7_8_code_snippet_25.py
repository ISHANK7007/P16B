async def _resolve_close_candidates(self, scored_candidates):
    """Handle close or contradictory cases with Bayesian methods"""
    
    # If scores are close, use Bayesian network to resolve
    if self._are_scores_close(scored_candidates[:2]):
        return await self._apply_bayesian_resolution(scored_candidates[:3])
    
    # Check for fundamental contradiction patterns
    if self._has_contradiction_pattern(scored_candidates):
        return await self._resolve_contradiction(scored_candidates)
    
    # Default to highest score with reduced confidence
    winner = scored_candidates[0]
    winner.consensus_confidence *= 0.8  # Reduce confidence due to competition
    return winner