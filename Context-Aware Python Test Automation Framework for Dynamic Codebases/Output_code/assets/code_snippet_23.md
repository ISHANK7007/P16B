class MutationLineage {
  parentPrompt
  appliedMutations = []  // Ordered sequence of mutations
  qualityMetricDeltas = {} // Keyed by metric type
  effectivenessScore
  
  calculateContribution(specificMutation) {
    // Isolate impact of specific mutation in the chain
  }
}