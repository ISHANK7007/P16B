function rankCandidates(candidates, context) {
  weights = adaptWeightsByContext(context)
  
  scores = candidates.map(candidate => {
    return {
      perplexityScore: measurePerplexity(candidate) * weights.perplexity,
      ruleScore: evaluateRuleCompliance(candidate) * weights.rules,
      modelPreference: getModelVote(candidate) * weights.modelVote,
      // Additional factors
      taskAlignment: evaluateTaskFit(candidate, context) * weights.task
    }
  })
  
  return computeWeightedRanking(candidates, scores)
}