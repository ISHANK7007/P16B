class MaintenanceCalendarIntegration:
    """Integrates with external maintenance and deployment calendars"""
    
    def __init__(self, exemption_manager: TimeWindowExemptionManager):
        self.exemption_manager = exemption_manager
        self.sync_state = {}
        
    async def sync_jira_maintenance_windows(self, jql_query: str) -> Dict:
        """Sync maintenance windows from JIRA"""
        # This would use your JIRA API client
        # jira_issues = await jira_client.search_issues(jql_query)
        
        # Placeholder for example
        jira_issues = [
            {
                "key": "OPS-123",
                "summary": "Database Maintenance",
                "fields": {
                    "customfield_start": "2023-06-10T20:00:00.000Z",
                    "customfield_end": "2023-06-11T02:00:00.000Z",
                    "components": ["database", "storage"],
                    "status": "Scheduled"
                }
            }
        ]
        
        results = {
            "created": 0,
            "updated": 0,
            "skipped": 0,
            "errors": 0
        }
        
        for issue in jira_issues:
            try:
                # Check if we've already synced this issue
                issue_key = issue["key"]
                
                if issue_key in self.sync_state:
                    # Update existing exemption
                    # This depends on your JIRA field mapping
                    start_time = datetime.fromisoformat(
                        issue["fields"]["customfield_start"].replace("Z", "+00:00"))
                    end_time = datetime.fromisoformat(
                        issue["fields"]["customfield_end"].replace("Z", "+00:00"))
                    
                    services = [c for c in issue["fields"]["components"]]
                    
                    updates = {
                        "name": issue["summary"],
                        "start_time": start_time,
                        "end_time": end_time,
                        "services": services
                    }
                    
                    exemption = self.exemption_manager.update_exemption(
                        self.sync_state[issue_key],
                        updates,
                        modifier="jira-sync"
                    )
                    
                    if exemption:
                        results["updated"] += 1
                    else:
                        results["errors"] += 1
                    
                else:
                    # Create new exemption
                    # This depends on your JIRA field mapping
                    start_time = datetime.fromisoformat(
                        issue["fields"]["customfield_start"].replace("Z", "+00:00"))
                    end_time = datetime.fromisoformat(
                        issue["fields"]["customfield_end"].replace("Z", "+00:00"))
                    
                    services = [c for c in issue["fields"]["components"]]
                    
                    exemption = self.exemption_manager.create_maintenance_window(
                        issue["summary"],
                        start_time,
                        end_time,
                        services,
                        creator="jira-sync",
                        jira_ticket=issue_key
                    )
                    
                    self.sync_state[issue_key] = exemption.id
                    results["created"] += 1
            
            except Exception as e:
                results["errors"] += 1
                
        return results
        
    async def sync_deploy_calendar(self, calendar_url: str) -> Dict:
        """Sync deployment windows from deployment calendar"""
        # This would use your deployment system's API
        # deployments = await deployment_api.get_scheduled_deployments(calendar_url)
        
        # Placeholder for example
        deployments = [
            {
                "id": "deploy-123",
                "name": "Frontend Deployment",
                "start": "2023-06-15T18:00:00Z",
                "end": "2023-06-15T20:00:00Z",
                "services": ["frontend", "api-gateway"],
                "environment": "production"
            }
        ]
        
        results = {
            "created": 0,
            "updated": 0,
            "skipped": 0,
            "errors": 0
        }
        
        for deploy in deployments:
            try:
                # Check if we've already synced this deployment
                deploy_id = deploy["id"]
                
                if deploy_id in self.sync_state:
                    # Update existing exemption
                    start_time = datetime.fromisoformat(
                        deploy["start"].replace("Z", "+00:00"))
                    end_time = datetime.fromisoformat(
                        deploy["end"].replace("Z", "+00:00"))
                    
                    services = deploy["services"]
                    environment = [deploy["environment"]]
                    
                    updates = {
                        "name": deploy["name"],
                        "start_time": start_time,
                        "end_time": end_time,
                        "services": services,
                        "environments": environment
                    }
                    
                    exemption = self.exemption_manager.update_exemption(
                        self.sync_state[deploy_id],
                        updates,
                        modifier="deploy-sync"
                    )
                    
                    if exemption:
                        results["updated"] += 1
                    else:
                        results["errors"] += 1
                    
                else:
                    # Create new exemption
                    start_time = datetime.fromisoformat(
                        deploy["start"].replace("Z", "+00:00"))
                    end_time = datetime.fromisoformat(
                        deploy["end"].replace("Z", "+00:00"))
                    
                    services = deploy["services"]
                    environment = [deploy["environment"]]
                    
                    exemption = self.exemption_manager.create_deploy_window(
                        deploy["name"],
                        start_time,
                        end_time,
                        services,
                        environment,
                        creator="deploy-sync"
                    )
                    
                    self.sync_state[deploy_id] = exemption.id
                    results["created"] += 1
            
            except Exception as e:
                results["errors"] += 1
                
        return results