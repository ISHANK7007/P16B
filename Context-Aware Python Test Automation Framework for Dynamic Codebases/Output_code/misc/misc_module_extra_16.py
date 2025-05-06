class AdaptiveTimeoutManager:
    """Manages timeouts adaptively based on historical performance"""
    
    def __init__(self):
        self.provider_latencies = {}  # Provider -> list of latencies
        self.format_multipliers = {
            "JSON": 1.5,  # JSON takes longer to validate
            "SQL": 1.3,
            "MARKDOWN": 1.0,
            "RAW_TEXT": 0.8
        }
    
    def record_latency(self, provider: LLMProvider, format_type: str, latency: float):
        """Record a latency observation"""
        key = (provider, format_type)
        if key not in self.provider_latencies:
            self.provider_latencies[key] = []
        
        # Keep last 100 observations
        self.provider_latencies[key].append(latency)
        if len(self.provider_latencies[key]) > 100:
            self.provider_latencies[key].pop(0)
    
    def get_timeout(self, provider: LLMProvider, format_type: str, default: float = 30.0) -> float:
        """Get appropriate timeout for a provider/format combination"""
        key = (provider, format_type)
        
        if key in self.provider_latencies and len(self.provider_latencies[key]) >= 5:
            # Calculate timeout based on historical data
            latencies = self.provider_latencies[key]
            median = sorted(latencies)[len(latencies)//2]
            p95 = sorted(latencies)[min(len(latencies)-1, int(len(latencies)*0.95))]
            
            # Use p95 with a safety margin
            return p95 * 1.5
        
        # Fall back to default with format multiplier
        format_mult = self.format_multipliers.get(format_type, 1.0)
        return default * format_mult