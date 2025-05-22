class CoordinationService:
    """Service for coordinating multi-team alert responses"""
    
    async def register_comment(self, correlation_id, team_id, comment, visibility="all"):
        """Register a comment on an alert, visible to specified teams"""
        comment_data = {
            "id": str(uuid.uuid4()),
            "correlation_id": correlation_id,
            "team_id": team_id,
            "comment": comment,
            "timestamp": datetime.utcnow().isoformat(),
            "visibility": visibility  # "all" or list of team_ids
        }
        
        await self.comment_store.add_comment(comment_data)
        
        # Notify other teams if comment is visible to them
        if visibility == "all" or isinstance(visibility, list):
            teams_to_notify = await self._get_teams_to_notify(
                correlation_id, 
                team_id, 
                visibility
            )
            
            for notify_team in teams_to_notify:
                await self.notify_team_of_comment(
                    correlation_id, 
                    notify_team, 
                    comment_data
                )
                
        return comment_data["id"]
    
    async def register_team_action(self, correlation_id, team_id, action, metadata=None):
        """Register an action taken by a team (acknowledge, escalate, resolve)"""
        action_data = {
            "id": str(uuid.uuid4()),
            "correlation_id": correlation_id,
            "team_id": team_id,
            "action": action,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        }
        
        await self.action_store.add_action(action_data)
        
        # Update path status in tracker
        if action == "acknowledge":
            await self.path_tracker.update_path_status(
                correlation_id, 
                team_id, 
                "acknowledged", 
                {"acknowledged_by": metadata.get("user_id")}
            )
        elif action == "resolve":
            await self.path_tracker.update_path_status(
                correlation_id, 
                team_id, 
                "resolved", 
                {
                    "resolved_by": metadata.get("user_id"),
                    "resolution_time": datetime.utcnow()
                }
            )
        
        # Notify other teams of this action
        other_teams = await self._get_other_teams(correlation_id, team_id)
        for other_team in other_teams:
            await self.notify_team_of_action(
                correlation_id, 
                other_team, 
                action_data
            )
            
        return action_data["id"]