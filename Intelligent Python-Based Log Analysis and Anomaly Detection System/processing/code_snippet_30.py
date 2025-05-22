class ParserChainSelector:
    """Selects the optimal parser chain for a given log source."""
    
    def __init__(self, resolver: ParserResolver):
        self.resolver = resolver
        self.chain_confidence_cache = {}
        
    async def select_chain(self, 
                         source: LogSource, 
                         sample_lines: Optional[List[str]] = None) -> Optional[str]:
        """
        Select the optimal parser chain for this source.
        
        Strategy:
        1. Check source format hint or explicit chain assignment
        2. Check file naming patterns and extensions
        3. Sample content and test with different chains
        4. If all else fails, use the default chain
        """
        # Check for explicit chain assignment
        if source.parser_chain:
            return source.parser_chain
            
        # If we have a format hint, map it to a chain
        if source.format_hint:
            chain = self._map_format_to_chain(source.format_hint)
            if chain:
                return chain
        
        # Check filename patterns
        if source.path:
            chain = self._chain_from_filename(source.path)
            if chain:
                return chain
                
        # If we have sample lines, test different chains
        if sample_lines:
            chain = await self._test_chains_on_samples(source, sample_lines)
            if chain:
                return chain
        
        # Fall back to default chain
        return self.resolver.get_default_chain()
    
    def _map_format_to_chain(self, format_hint: str) -> Optional[str]:
        """Map a format hint to a parser chain."""
        format_to_chain = {
            'json': 'application',
            'syslog': 'linux_system',
            'journald': 'linux_system',
            'apache_access': 'web_server',
            'apache_error': 'web_server',
            'nginx': 'web_server',
            'python': 'application',
            'custom_app': 'application'
        }
        
        return format_to_chain.get(format_hint.lower())
    
    def _chain_from_filename(self, path: str) -> Optional[str]:
        """Determine parser chain from filename patterns."""
        filename = os.path.basename(path).lower()
        
        # Web server logs
        if any(pattern in filename for pattern in 
              ['access', 'error', 'nginx', 'apache', 'httpd']):
            return 'web_server'
            
        # System logs
        if any(pattern in filename for pattern in 
              ['syslog', 'system', 'kernel', 'auth', 'daemon', 'journal']):
            return 'linux_system'
            
        # Application logs
        if any(pattern in filename for pattern in 
              ['app', 'application', 'service', '.log']):
            return 'application'
            
        # Database logs
        if any(pattern in filename for pattern in 
              ['db', 'database', 'mysql', 'postgres', 'mongo']):
            return 'database'
            
        return None
    
    async def _test_chains_on_samples(self, 
                                     source: LogSource, 
                                     sample_lines: List[str]) -> Optional[str]:
        """Test different parser chains on sample lines to find the best match."""
        if not sample_lines:
            return None
            
        # Get all available chains
        chains = self.resolver._chains.keys()
        
        # Test each chain on the sample lines
        chain_scores = {}
        
        for chain_name in chains:
            # Check if we have cached results for this source+chain
            cache_key = (source.source_id, chain_name)
            if cache_key in self.chain_confidence_cache:
                chain_scores[chain_name] = self.chain_confidence_cache[cache_key]
                continue
                
            # Test this chain on the samples
            successful_parses = 0
            total_confidence = 0.0
            
            for line in sample_lines:
                entry, _ = self.resolver.resolve_with_trace(line, chain_name)
                if entry and hasattr(entry, 'confidence') and entry.confidence > 0.5:
                    successful_parses += 1
                    total_confidence += entry.confidence
            
            # Calculate the score for this chain
            if successful_parses > 0:
                avg_confidence = total_confidence / successful_parses
                success_rate = successful_parses / len(sample_lines)
                
                # Combined score that favors both high confidence and high success rate
                score = avg_confidence * success_rate
                
                chain_scores[chain_name] = score
                
                # Cache the result
                self.chain_confidence_cache[cache_key] = score
        
        # Select the chain with the highest score
        if chain_scores:
            best_chain = max(chain_scores.items(), key=lambda x: x[1])[0]
            return best_chain
            
        return None