class CoordinatedDeEscalation:
    """Handles de-escalation coordination across teams"""
    
    async def coordinate_de_escalation(self, correlation_id, action, evidence):
        """Coordinate de-escalation across all teams for a correlated alert"""
        # Get all teams involved with this alert
        team_paths = await self.path_tracker.get_paths(correlation_id)
        
        if not team_paths or len(team_paths) <= 1:
            # Not a multi-team alert or only one team left
            return True
            
        # Check team-specific requirements for de-escalation
        team_approvals = {}
        blocking_teams = []
        
        for team_id, path in team_paths.items():
            # Skip already resolved paths
            if path["status"] == "resolved":
                team_approvals[team_id] = True
                continue
                
            # Check if this team has specific override requirements
            approval = await self._check_team_de_escalation_criteria(
                team_id, 
                correlation_id, 
                action, 
                evidence
            )
            
            team_approvals[team_id] = approval
            if not approval:
                blocking_teams.append(team_id)
                
        # If no teams are blocking, proceed with de-escalation
        if not blocking_teams:
            await self._apply_to_all_teams(correlation_id, action, evidence)
            return True
        else:
            # Create a de-escalation request that requires approval
            await self._create_approval_request(
                correlation_id, 
                action, 
                evidence, 
                blocking_teams
            )
            return False
            
    async def _apply_to_all_teams(self, correlation_id, action, evidence):
        """Apply de-escalation to all team paths"""
        # Get the original alert
        alert_context = await self.correlation_store.get_context(correlation_id)
        
        # Create de-escalation record
        de_escalation_id = str(uuid.uuid4())
        record = {
            "id": de_escalation_id,
            "correlation_id": correlation_id,
            "action": action,
            "evidence": evidence,
            "timestamp": datetime.utcnow().isoformat(),
            "status": "applied",
            "applied_by": action.initiated_by or "system"
        }
        
        await self.de_escalation_store.store_record(record)
        
        # Apply to each team path
        team_paths = await self.path_tracker.get_paths(correlation_id)
        
        for team_id, path in team_paths.items():
            if path["status"] != "resolved":
                # Update path status
                new_status = "resolved" if action.target_level == 0 else "updated" 
                await self.path_tracker.update_path_status(
                    correlation_id,
                    team_id,
                    new_status,
                    {
                        "de_escalation_id": de_escalation_id,
                        "last_level": path.get("escalation_level", 0),
                        "new_level": action.target_level,
                    }
                )
                
                # Notify the team
                await self.notification_service.notify_de_escalation(
                    team_id,
                    correlation_id,
                    record
                )
        
        return True