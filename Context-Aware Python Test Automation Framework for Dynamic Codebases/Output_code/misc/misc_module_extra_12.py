class DynamicProviderRouter:
    """Routes mutations to the most appropriate provider based on various factors"""
    
    def __init__(self, 
                provider_throughput: Dict[LLMProvider, int],
                provider_costs: Dict[LLMProvider, float],
                format_preferences: Dict[PromptFormat, List[LLMProvider]]):
        self.provider_throughput = provider_throughput
        self.provider_costs = provider_costs
        self.format_preferences = format_preferences
        self.provider_usage: Dict[LLMProvider, int] = {p: 0 for p in provider_throughput}
        self.lock = asyncio.Lock()
    
    async def select_provider(self, 
                           mutation: MutationTrace, 
                           budget_constraint: Optional[float] = None) -> LLMProvider:
        """Select the best provider for a mutation"""
        async with self.lock:
            # Get preferred providers for this format
            format_type = mutation.prompt_format
            preferred = self.format_preferences.get(format_type, list(self.provider_throughput.keys()))
            
            # Filter by budget if specified
            if budget_constraint is not None:
                # Estimate token count (simple approximation)
                token_count = len(mutation.original_prompt.split()) + len(mutation.mutated_prompt.split())
                affordable = [
                    p for p in preferred 
                    if token_count * self.provider_costs.get(p, 0) <= budget_constraint
                ]
                if affordable:
                    preferred = affordable
            
            # Calculate load factor for each provider
            load_factors = {}
            for provider in preferred:
                throughput = self.provider_throughput.get(provider, 1)
                usage = self.provider_usage.get(provider, 0)
                
                # Lower load factor is better
                load_factors[provider] = usage / throughput
            
            # Select the provider with the lowest load factor
            selected = min(load_factors.items(), key=lambda x: x[1])[0]
            
            # Update usage counter
            self.provider_usage[selected] += 1
            
            return selected