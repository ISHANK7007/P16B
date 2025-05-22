class BlackoutPeriodManager:
    """Manages extended blackout periods and change freezes"""
    
    def __init__(self, exemption_manager: TimeWindowExemptionManager):
        self.exemption_manager = exemption_manager
        
    def schedule_holiday(
        self,
        name: str,
        date: datetime.date,
        action: ExemptionAction = ExemptionAction.DOWNGRADE,
        max_criticality: str = "HIGH"
    ) -> TimeWindowExemption:
        """Schedule a holiday blackout period"""
        # Create a whole day exemption
        start_time = datetime.combine(date, time(0, 0, 0))
        end_time = datetime.combine(date, time(23, 59, 59))
        
        exemption = TimeWindowExemption(
            name=name,
            description=f"Holiday: {name}",
            exemption_type=ExemptionType.HOLIDAY,
            action=action,
            start_time=start_time,
            end_time=end_time,
            timezone="UTC",  # Default, can be changed
            recurrence=RecurrenceType.ONCE,
            max_criticality=max_criticality,
            created_by="blackout-manager"
        )
        
        self.exemption_manager.add_exemption(exemption)
        return exemption
        
    def schedule_change_freeze(
        self,
        name: str,
        start_date: datetime.date,
        end_date: datetime.date,
        services: Optional[List[str]] = None,
        action: ExemptionAction = ExemptionAction.DELAY
    ) -> TimeWindowExemption:
        """Schedule a change freeze period"""
        # Create a multi-day exemption
        start_time = datetime.combine(start_date, time(0, 0, 0))
        end_time = datetime.combine(end_date, time(23, 59, 59))
        
        exemption = TimeWindowExemption(
            name=name,
            description=f"Change Freeze: {name}",
            exemption_type=ExemptionType.FREEZE,
            action=action,
            start_time=start_time,
            end_time=end_time,
            timezone="UTC",  # Default, can be changed
            recurrence=RecurrenceType.ONCE,
            services=services or [],
            created_by="blackout-manager"
        )
        
        self.exemption_manager.add_exemption(exemption)
        return exemption
        
    def schedule_recurring_quiet_hours(
        self,
        name: str,
        weekdays: List[int],  # 0=Monday, 6=Sunday
        start_hour: int,
        end_hour: int,
        timezone: str = "UTC",
        action: ExemptionAction = ExemptionAction.DOWNGRADE
    ) -> TimeWindowExemption:
        """Schedule recurring quiet hours"""
        # Create start and end times for the recurring window
        today = datetime.now().date()
        start_time = datetime.combine(today, time(start_hour, 0, 0))
        
        # Handle overnight windows
        if end_hour <= start_hour:
            end_time = datetime.combine(today + timedelta(days=1), time(end_hour, 0, 0))
        else:
            end_time = datetime.combine(today, time(end_hour, 0, 0))
        
        exemption = TimeWindowExemption(
            name=name,
            description=f"Quiet Hours: {name}",
            exemption_type=ExemptionType.QUIET_HOURS,
            action=action,
            start_time=start_time,
            end_time=end_time,
            timezone=timezone,
            recurrence=RecurrenceType.WEEKLY,
            recurrence_days=weekdays,
            created_by="blackout-manager"
        )
        
        self.exemption_manager.add_exemption(exemption)
        return exemption