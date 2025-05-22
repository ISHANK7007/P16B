class OptimizedDependencyGraphManager:
    def __init__(self, service_discovery, cache_manager):
        self.service_discovery = service_discovery
        self.cache_manager = cache_manager
        self.topology_refresh_interval = adaptive_refresh_interval()
        
    def get_dependency_subgraph(self, service_scope, anomaly_context=None):
        # Try cached version first
        cached_graph = self.cache_manager.get_cached_topology(service_scope)
        
        if cached_graph and not self._requires_refresh(cached_graph, anomaly_context):
            # Use cached version with delta-diffing for recent changes
            live_changes = self._detect_topology_changes(cached_graph)
            if live_changes:
                return self._apply_delta_diff(cached_graph, live_changes)
            return cached_graph
        
        # Fall back to regenerating the relevant subgraph
        return self._generate_fresh_dependency_graph(service_scope)