class AgentConnectionPoolManager:
    """
    Manages connection pools for each agent to enable efficient resource
    utilization during concurrent edit sessions.
    """
    def __init__(self, max_connections_per_agent=5, idle_timeout=60):
        self.connection_pools = {}
        self.max_connections_per_agent = max_connections_per_agent
        self.idle_timeout = idle_timeout
        self.stats = {
            "connections_created": 0,
            "connections_reused": 0,
            "peak_concurrent": 0
        }
        
    def get_connection(self, agent_id):
        """Get a connection for an agent, creating a pool if needed"""
        if agent_id not in self.connection_pools:
            self.connection_pools[agent_id] = ConnectionPool(
                max_size=self.max_connections_per_agent,
                idle_timeout=self.idle_timeout
            )
            
        conn = self.connection_pools[agent_id].acquire()
        
        # Update stats
        if conn.is_new:
            self.stats["connections_created"] += 1
        else:
            self.stats["connections_reused"] += 1
            
        current_count = sum(
            pool.active_count for pool in self.connection_pools.values()
        )
        self.stats["peak_concurrent"] = max(
            self.stats["peak_concurrent"], current_count)
            
        return conn
        
    def release_connection(self, agent_id, connection):
        """Release a connection back to the pool"""
        if agent_id in self.connection_pools:
            self.connection_pools[agent_id].release(connection)
            
    def cleanup_idle_pools(self):
        """Clean up idle connection pools"""
        for agent_id, pool in list(self.connection_pools.items()):
            if pool.active_count == 0 and pool.idle_count == 0:
                del self.connection_pools[agent_id]