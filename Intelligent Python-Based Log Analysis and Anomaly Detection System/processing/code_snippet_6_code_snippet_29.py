class ExemptionDashboardAPI:
    """API for exemption management dashboard"""
    
    def __init__(
        self, 
        exemption_manager: TimeWindowExemptionManager,
        recurring_scheduler: RecurringScheduleManager,
        maintenance_integration: MaintenanceCalendarIntegration,
        blackout_manager: BlackoutPeriodManager
    ):
        self.exemption_manager = exemption_manager
        self.scheduler = recurring_scheduler
        self.maintenance_integration = maintenance_integration
        self.blackout_manager = blackout_manager
        
    def get_active_exemptions(self) -> List[Dict]:
        """Get currently active exemptions"""
        active = self.exemption_manager.get_active_exemptions()
        return [ex.to_dict() for ex in active]
        
    def get_upcoming_exemptions(self, days: int = 7) -> List[Dict]:
        """Get exemptions starting in the next N days"""
        now = datetime.now()
        future = now + timedelta(days=days)
        
        upcoming = []
        for exemption in self.exemption_manager.exemptions.values():
            if exemption.start_time > now and exemption.start_time < future:
                upcoming.append(exemption.to_dict())
                
        return upcoming
        
    def get_exemption_by_id(self, exemption_id: str) -> Optional[Dict]:
        """Get exemption details by ID"""
        if exemption_id in self.exemption_manager.exemptions:
            return self.exemption_manager.exemptions[exemption_id].to_dict()
        return None
        
    def create_exemption(self, exemption_data: Dict) -> Dict:
        """Create a new exemption from API data"""
        exemption = TimeWindowExemption.from_dict(exemption_data)
        exemption_id = self.exemption_manager.add_exemption(exemption)
        return {"id": exemption_id, "status": "created"}
        
    def update_exemption(self, exemption_id: str, updates: Dict, modifier: str) -> Dict:
        """Update an existing exemption"""
        exemption = self.exemption_manager.update_exemption(exemption_id, updates, modifier)
        if exemption:
            return {"id": exemption_id, "status": "updated"}
        return {"id": exemption_id, "status": "error", "message": "Exemption not found"}
        
    def delete_exemption(self, exemption_id: str) -> Dict:
        """Delete an exemption"""
        success = self.exemption_manager.delete_exemption(exemption_id)
        if success:
            return {"id": exemption_id, "status": "deleted"}
        return {"id": exemption_id, "status": "error", "message": "Exemption not found"}
        
    def get_exemption_stats(self) -> Dict:
        """Get statistics about exemptions"""
        exemptions = self.exemption_manager.exemptions.values()
        
        by_type = {}
        for ex in exemptions:
            ex_type = ex.exemption_type.name
            if ex_type not in by_type:
                by_type[ex_type] = 0
            by_type[ex_type] += 1
            
        active_count = len(self.exemption_manager.get_active_exemptions())
        
        return {
            "total": len(exemptions),
            "active": active_count,
            "by_type": by_type
        }
        
    def get_delayed_escalations(self) -> Dict:
        """Get statistics about delayed escalations"""
        delayed = self.exemption_manager.delayed_escalations.values()
        
        pending = [d for d in delayed if not d.executed]
        executed = [d for d in delayed if d.executed]
        
        return {
            "total": len(delayed),
            "pending": len(pending),
            "executed": len(executed),
            "next_execution": min([d.scheduled_time for d in pending], default=None)
        }
        
    def get_batched_alerts(self) -> Dict:
        """Get statistics about batched alerts"""
        batched = self.exemption_manager.batched_alerts.values()
        
        pending = [b for b in batched if not b.delivered]
        delivered = [b for b in batched if b.delivered]
        
        total_alerts = sum(len(b.alerts) for b in batched)
        
        return {
            "total_batches": len(batched),
            "pending_batches": len(pending),
            "delivered_batches": len(delivered),
            "total_alerts": total_alerts
        }
        
    async def sync_maintenance_windows(self) -> Dict:
        """Sync maintenance windows from external systems"""
        jira_result = await self.maintenance_integration.sync_jira_maintenance_windows(
            "project = OPS AND type = 'Maintenance' AND status != 'Completed'"
        )
        
        deploy_result = await self.maintenance_integration.sync_deploy_calendar(
            "https://example.com/deploy-calendar"
        )
        
        return {
            "jira_sync": jira_result,
            "deploy_sync": deploy_result,
            "timestamp": datetime.now().isoformat()
        }
        
    def schedule_holiday(self, name: str, date: str) -> Dict:
        """Schedule a holiday exemption"""
        date_obj = datetime.strptime(date, "%Y-%m-%d").date()
        exemption = self.blackout_manager.schedule_holiday(name, date_obj)
        return {"id": exemption.id, "status": "created"}