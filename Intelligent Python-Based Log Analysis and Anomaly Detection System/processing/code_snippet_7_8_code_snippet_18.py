class RoutingPath:
    def __init__(self, team_id, channels, priority, context_scope, escalation_policy):
        self.team_id = team_id
        self.channels = channels  # List of notification channels
        self.priority = priority  # Routing priority for this team
        self.context_scope = context_scope  # Team-specific context parameters
        self.escalation_policy = escalation_policy  # Team's escalation policy ID
        self.status = "pending"
        self.forked_time = datetime.utcnow()

class RoutingContextRecord:
    def __init__(self, correlation_id, original_alert, paths, created_at):
        self.correlation_id = correlation_id
        self.original_alert = original_alert
        self.paths = paths
        self.created_at = created_at
        self.status = {path.team_id: "pending" for path in paths}
        self.resolution = {}
        self.is_resolved = False

class MultiPathTracker:
    """Tracks status of alerts across multiple routing paths"""
    
    def __init__(self):
        self.path_store = {}  # correlation_id -> {team_id -> path_status}
        
    def register_path(self, correlation_id, team_id, escalation_policy):
        """Register a new routing path"""
        if correlation_id not in self.path_store:
            self.path_store[correlation_id] = {}
            
        self.path_store[correlation_id][team_id] = {
            "status": "active",
            "escalation_policy": escalation_policy,
            "escalation_level": 0,
            "notified_at": datetime.utcnow(),
            "acknowledged_by": None,
            "resolved_by": None,
            "resolution_time": None
        }
    
    async def update_path_status(self, correlation_id, team_id, status, metadata=None):
        """Update status of a specific routing path"""
        if correlation_id in self.path_store and team_id in self.path_store[correlation_id]:
            self.path_store[correlation_id][team_id].update({
                "status": status,
                "last_updated": datetime.utcnow(),
                **(metadata or {})
            })
            
            # Check if all paths are resolved
            await self._check_all_paths_resolution(correlation_id)
            
            return True
        return False
    
    async def _check_all_paths_resolution(self, correlation_id):
        """Check if all paths for an alert are resolved"""
        if correlation_id not in self.path_store:
            return False
            
        paths = self.path_store[correlation_id]
        all_resolved = all(p["status"] == "resolved" for p in paths.values())
        
        if all_resolved:
            # All teams have resolved their paths - mark alert as fully resolved
            await self._mark_fully_resolved(correlation_id)
            
        return all_resolved
    
    async def _mark_fully_resolved(self, correlation_id):
        """Mark an alert as fully resolved across all teams"""
        # Update status in correlation store
        await self.correlation_store.update_status(correlation_id, "resolved")
        
        # Notify all teams about cross-team resolution
        teams = list(self.path_store[correlation_id].keys())
        resolution_data = {team: self.path_store[correlation_id][team] for team in teams}
        
        for team in teams:
            await self.notify_cross_team_resolution(correlation_id, team, resolution_data)