async def _resolve_contradiction(self, candidates):
    """Resolve fundamental contradictions between sources"""
    
    # Classify the contradiction type
    contradiction_type = self._classify_contradiction(candidates)
    
    if contradiction_type == "LLM_VS_METRIC":
        # When LLM and metric-based analysis fundamentally disagree
        return await self._resolve_llm_metric_contradiction(candidates)
    elif contradiction_type == "DEPENDENCY_DIRECTION":
        # When dependency analysis suggests opposite causal direction than other sources
        return await self._resolve_dependency_direction_contradiction(candidates)
    elif contradiction_type == "MULTI_ROOT_POSSIBILITY":
        # When evidence suggests multiple independent root causes
        return self._create_multi_root_consensus(candidates)
    else:
        # For other cases, use specialized arbitration
        return await self._apply_arbitration_rules(candidates)