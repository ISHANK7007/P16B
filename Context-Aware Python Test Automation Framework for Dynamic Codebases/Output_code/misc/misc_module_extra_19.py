# Provider circuit breaker
class ProviderCircuitBreaker:
    def __init__(self):
        self.failure_counts = {}
        self.circuit_open = {}
        
    async def check_before_request(self, provider):
        if self.circuit_open.get(provider, False):
            # Circuit is open, check if we should retry
            # If should retry, close circuit tentatively
            pass
        return True  # Allow request
        
    def record_result(self, provider, success):
        if not success:
            self.failure_counts[provider] = self.failure_counts.get(provider, 0) + 1
            if self.failure_counts[provider] >= 5:
                # Open circuit after 5 consecutive failures
                self.circuit_open[provider] = True
        else:
            # Reset counter on success
            self.failure_counts[provider] = 0
            self.circuit_open[provider] = False