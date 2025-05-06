class TransformationCache {
  // Fast, fixed-size cache for high-frequency patterns
  lruCache = new LRUCache<VersionTag, PromptDelta>(size=1000)
  
  // Secondary cache with more sophisticated eviction
  stableCache = new StabilizedCache<VersionTag, PromptDelta>(
    retentionPolicy=frequencyWeightedWithDecay
  )
  
  // Background precomputation of likely transformations
  predictiveGenerator = new PredictiveTransformGenerator()
}