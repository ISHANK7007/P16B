class MutationBrancher {
  produceVariants(basePrompt, mutationSet, diversityTarget) {
    variants = []
    coverageMap = new SemanticCoverageMap()
    
    for (mutation in prioritizedMutations) {
      newVariant = applyMutation(basePrompt, mutation)
      if (increaseDiversity(coverageMap, newVariant)) {
        variants.add(newVariant)
      }
    }
    
    return selectOptimalSubset(variants, diversityTarget)
  }
}