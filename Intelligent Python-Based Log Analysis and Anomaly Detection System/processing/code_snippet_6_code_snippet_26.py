from enum import Enum, auto
from datetime import datetime, timedelta, time
from typing import Dict, List, Set, Tuple, Optional, Any, Callable, Union
from dataclasses import dataclass, field
import re
import uuid
import pytz

class ExemptionType(Enum):
    """Types of escalation exemptions"""
    MAINTENANCE = auto()        # Planned maintenance windows
    DEPLOY = auto()             # Deployment windows
    QUIET_HOURS = auto()        # After-hours/low-priority periods
    FREEZE = auto()             # Change freeze periods
    INCIDENT = auto()           # Active incident handling periods
    HOLIDAY = auto()            # Organization holidays
    LOAD_TEST = auto()          # Performance test windows
    CUSTOMIZED = auto()         # Custom-defined exemptions

class ExemptionAction(Enum):
    """Actions to take during exemption windows"""
    SUPPRESS = auto()           # Don't generate any alerts
    DELAY = auto()              # Delay alerts until window ends
    DOWNGRADE = auto()          # Reduce severity/urgency
    REDIRECT = auto()           # Send to alternative stakeholders
    BATCH = auto()              # Batch alerts for periodic delivery
    LOG_ONLY = auto()           # Record alerts without notification

class RecurrenceType(Enum):
    """Types of time window recurrence"""
    ONCE = auto()               # One-time window
    DAILY = auto()              # Repeats daily
    WEEKLY = auto()             # Repeats weekly
    MONTHLY = auto()            # Repeats monthly
    CUSTOM = auto()             # Custom recurrence pattern

@dataclass
class TimeWindowExemption:
    """Defines a time period where normal escalation rules are modified"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    exemption_type: ExemptionType = ExemptionType.MAINTENANCE
    action: ExemptionAction = ExemptionAction.DELAY
    
    # Time window definition
    start_time: datetime = None
    end_time: datetime = None
    timezone: str = "UTC"
    recurrence: RecurrenceType = RecurrenceType.ONCE
    recurrence_end: Optional[datetime] = None
    recurrence_days: List[int] = field(default_factory=list)  # Days for weekly/monthly (0=Monday for weekly, 1-31 for monthly)
    
    # Scope definition
    services: List[str] = field(default_factory=list)
    environments: List[str] = field(default_factory=list)
    anomaly_types: List[str] = field(default_factory=list)
    jira_tickets: List[str] = field(default_factory=list)
    max_criticality: Optional[str] = None  # Maximum Service Criticality to affect
    
    # Custom action parameters
    delay_minutes: int = 0
    alternative_stakeholders: List[str] = field(default_factory=list)
    batch_minutes: int = 60
    
    # Metadata
    created_by: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    last_modified: datetime = field(default_factory=datetime.now)
    last_modified_by: str = ""
    
    # Runtime tracking
    applied_count: int = 0
    last_applied: Optional[datetime] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "exemption_type": self.exemption_type.name,
            "action": self.action.name,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "timezone": self.timezone,
            "recurrence": self.recurrence.name,
            "recurrence_end": self.recurrence_end.isoformat() if self.recurrence_end else None,
            "recurrence_days": self.recurrence_days,
            "services": self.services,
            "environments": self.environments,
            "anomaly_types": self.anomaly_types,
            "jira_tickets": self.jira_tickets,
            "max_criticality": self.max_criticality,
            "delay_minutes": self.delay_minutes,
            "alternative_stakeholders": self.alternative_stakeholders,
            "batch_minutes": self.batch_minutes,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_modified": self.last_modified.isoformat() if self.last_modified else None,
            "last_modified_by": self.last_modified_by,
            "applied_count": self.applied_count,
            "last_applied": self.last_applied.isoformat() if self.last_applied else None
        }
    
    @staticmethod
    def from_dict(data: Dict) -> 'TimeWindowExemption':
        """Create from dictionary"""
        exemption = TimeWindowExemption()
        
        for key, value in data.items():
            if key == 'exemption_type':
                exemption.exemption_type = ExemptionType[value]
            elif key == 'action':
                exemption.action = ExemptionAction[value]
            elif key == 'recurrence':
                exemption.recurrence = RecurrenceType[value]
            elif key == 'start_time' and value:
                exemption.start_time = datetime.fromisoformat(value)
            elif key == 'end_time' and value:
                exemption.end_time = datetime.fromisoformat(value)
            elif key == 'recurrence_end' and value:
                exemption.recurrence_end = datetime.fromisoformat(value)
            elif key == 'created_at' and value:
                exemption.created_at = datetime.fromisoformat(value)
            elif key == 'last_modified' and value:
                exemption.last_modified = datetime.fromisoformat(value)
            elif key == 'last_applied' and value:
                exemption.last_applied = datetime.fromisoformat(value)
            elif hasattr(exemption, key):
                setattr(exemption, key, value)
                
        return exemption
        
    def is_active(self, current_time: Optional[datetime] = None) -> bool:
        """Check if this exemption is currently active"""
        now = current_time or datetime.now(pytz.timezone(self.timezone))
        
        if self.recurrence == RecurrenceType.ONCE:
            # One-time window
            return self.start_time <= now <= self.end_time
            
        # Check recurrence end date if set
        if self.recurrence_end and now > self.recurrence_end:
            return False
            
        # For recurring windows, check if current time is within daily window
        current_time = now.time()
        window_start = self.start_time.time()
        window_end = self.end_time.time()
        
        in_daily_window = window_start <= current_time <= window_end
        if not in_daily_window:
            return False
            
        # Check day-specific recurrence
        if self.recurrence == RecurrenceType.DAILY:
            return True
        elif self.recurrence == RecurrenceType.WEEKLY:
            # 0 = Monday, 6 = Sunday in Python's weekday()
            return now.weekday() in self.recurrence_days
        elif self.recurrence == RecurrenceType.MONTHLY:
            return now.day in self.recurrence_days
        elif self.recurrence == RecurrenceType.CUSTOM:
            # Custom recurrence handled elsewhere
            return False
            
        return False

@dataclass
class DelayedEscalation:
    """Represents an escalation that has been delayed"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    anomaly_fingerprint: str = ""
    cluster_id: Optional[str] = None
    exemption_id: str = ""
    original_time: datetime = None
    scheduled_time: datetime = None
    executed: bool = False
    execution_time: Optional[datetime] = None
    escalation_level: str = ""
    stakeholders: List[str] = field(default_factory=list)
    service: str = ""
    anomaly_type: str = ""
    
    def is_due(self, current_time: Optional[datetime] = None) -> bool:
        """Check if this delayed escalation is due for execution"""
        if self.executed:
            return False
            
        now = current_time or datetime.now()
        return now >= self.scheduled_time

@dataclass
class BatchedAlerts:
    """Collection of alerts to be delivered in a batch"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    exemption_id: str = ""
    stakeholder_id: str = ""
    alerts: List[Dict] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)
    delivered: bool = False
    scheduled_delivery: datetime = None
    
    def add_alert(self, alert_data: Dict) -> None:
        """Add an alert to the batch"""
        self.alerts.append(alert_data)
        self.last_updated = datetime.now()
    
    def is_due(self, current_time: Optional[datetime] = None) -> bool:
        """Check if this batch is due for delivery"""
        if self.delivered:
            return False
            
        now = current_time or datetime.now()
        return now >= self.scheduled_delivery
        
    def get_summary(self) -> Dict:
        """Get a summary of alerts in this batch"""
        services = set()
        anomaly_types = set()
        fingerprints = set()
        
        for alert in self.alerts:
            services.add(alert.get("service", ""))
            anomaly_types.add(alert.get("anomaly_type", ""))
            fingerprints.add(alert.get("fingerprint", ""))
            
        return {
            "id": self.id,
            "count": len(self.alerts),
            "services": list(services),
            "anomaly_types": list(anomaly_types),
            "unique_alerts": len(fingerprints),
            "created_at": self.created_at,
            "scheduled_delivery": self.scheduled_delivery
        }

class TimeWindowExemptionManager:
    """Manages time window exemptions for the escalation engine"""
    
    def __init__(self):
        self.exemptions: Dict[str, TimeWindowExemption] = {}
        self.delayed_escalations: Dict[str, DelayedEscalation] = {}
        self.batched_alerts: Dict[str, BatchedAlerts] = {}
        self.exemption_tags: Dict[str, Set[str]] = {}  # tag -> exemption_ids
        
        # Default quiet hours
        self._init_default_exemptions()
    
    def _init_default_exemptions(self) -> None:
        """Initialize default exemptions"""
        # Default quiet hours (weekdays 8pm-8am)
        weekday_nights = TimeWindowExemption(
            name="Weeknight Quiet Hours",
            description="Reduce noise during weeknights",
            exemption_type=ExemptionType.QUIET_HOURS,
            action=ExemptionAction.DOWNGRADE,
            start_time=datetime.combine(datetime.now().date(), time(20, 0)),
            end_time=datetime.combine(datetime.now().date() + timedelta(days=1), time(8, 0)),
            timezone="UTC",
            recurrence=RecurrenceType.WEEKLY,
            recurrence_days=[0, 1, 2, 3, 4]  # Monday-Friday
        )
        
        # Weekend quiet hours (all day Saturday/Sunday)
        weekend = TimeWindowExemption(
            name="Weekend Quiet Hours",
            description="Reduce noise during weekends",
            exemption_type=ExemptionType.QUIET_HOURS,
            action=ExemptionAction.DOWNGRADE,
            start_time=datetime.combine(datetime.now().date(), time(0, 0)),
            end_time=datetime.combine(datetime.now().date(), time(23, 59, 59)),
            timezone="UTC",
            recurrence=RecurrenceType.WEEKLY,
            recurrence_days=[5, 6]  # Saturday, Sunday
        )
        
        self.add_exemption(weekday_nights)
        self.add_exemption(weekend)
    
    def add_exemption(self, exemption: TimeWindowExemption) -> str:
        """Add a new time window exemption"""
        self.exemptions[exemption.id] = exemption
        
        # Add to tags
        self._update_exemption_tags(exemption)
        
        return exemption.id
    
    def _update_exemption_tags(self, exemption: TimeWindowExemption) -> None:
        """Update tag indexes for an exemption"""
        # Add service tags
        for service in exemption.services:
            tag = f"service:{service}"
            if tag not in self.exemption_tags:
                self.exemption_tags[tag] = set()
            self.exemption_tags[tag].add(exemption.id)
            
        # Add environment tags
        for env in exemption.environments:
            tag = f"env:{env}"
            if tag not in self.exemption_tags:
                self.exemption_tags[tag] = set()
            self.exemption_tags[tag].add(exemption.id)
            
        # Add anomaly type tags
        for atype in exemption.anomaly_types:
            tag = f"anomaly_type:{atype}"
            if tag not in self.exemption_tags:
                self.exemption_tags[tag] = set()
            self.exemption_tags[tag].add(exemption.id)
            
        # Add exemption type tag
        tag = f"type:{exemption.exemption_type.name}"
        if tag not in self.exemption_tags:
            self.exemption_tags[tag] = set()
        self.exemption_tags[tag].add(exemption.id)
    
    def update_exemption(
        self, 
        exemption_id: str, 
        updates: Dict,
        modifier: str = ""
    ) -> Optional[TimeWindowExemption]:
        """Update an existing exemption"""
        if exemption_id not in self.exemptions:
            return None
            
        exemption = self.exemptions[exemption_id]
        
        for key, value in updates.items():
            if key == 'exemption_type' and isinstance(value, str):
                exemption.exemption_type = ExemptionType[value]
            elif key == 'action' and isinstance(value, str):
                exemption.action = ExemptionAction[value]
            elif key == 'recurrence' and isinstance(value, str):
                exemption.recurrence = RecurrenceType[value]
            elif key == 'start_time' and value:
                if isinstance(value, str):
                    exemption.start_time = datetime.fromisoformat(value)
                else:
                    exemption.start_time = value
            elif key == 'end_time' and value:
                if isinstance(value, str):
                    exemption.end_time = datetime.fromisoformat(value)
                else:
                    exemption.end_time = value
            elif key == 'recurrence_end' and value:
                if isinstance(value, str):
                    exemption.recurrence_end = datetime.fromisoformat(value)
                else:
                    exemption.recurrence_end = value
            elif hasattr(exemption, key):
                setattr(exemption, key, value)
        
        # Update metadata
        exemption.last_modified = datetime.now()
        exemption.last_modified_by = modifier
        
        # Update tags
        self._update_exemption_tags(exemption)
        
        return exemption
    
    def delete_exemption(self, exemption_id: str) -> bool:
        """Delete an exemption"""
        if exemption_id not in self.exemptions:
            return False
            
        # Remove from tag indexes
        for tag_set in self.exemption_tags.values():
            if exemption_id in tag_set:
                tag_set.remove(exemption_id)
                
        # Delete exemption
        del self.exemptions[exemption_id]
        
        return True
    
    def get_active_exemptions(
        self, 
        current_time: Optional[datetime] = None, 
        service: Optional[str] = None,
        environment: Optional[str] = None,
        anomaly_type: Optional[str] = None
    ) -> List[TimeWindowExemption]:
        """Get currently active exemptions, optionally filtered"""
        now = current_time or datetime.now()
        
        # Start with exemption candidates
        candidates = self.exemptions.values()
        
        # Apply filters
        if service:
            service_tag = f"service:{service}"
            if service_tag in self.exemption_tags:
                service_exemptions = {
                    self.exemptions[ex_id] 
                    for ex_id in self.exemption_tags[service_tag]
                }
                candidates = [ex for ex in candidates if ex in service_exemptions or not ex.services]
                
        if environment:
            env_tag = f"env:{environment}"
            if env_tag in self.exemption_tags:
                env_exemptions = {
                    self.exemptions[ex_id] 
                    for ex_id in self.exemption_tags[env_tag]
                }
                candidates = [ex for ex in candidates if ex in env_exemptions or not ex.environments]
                
        if anomaly_type:
            type_tag = f"anomaly_type:{anomaly_type}"
            if type_tag in self.exemption_tags:
                type_exemptions = {
                    self.exemptions[ex_id] 
                    for ex_id in self.exemption_tags[type_tag]
                }
                candidates = [ex for ex in candidates if ex in type_exemptions or not ex.anomaly_types]
        
        # Filter to active exemptions
        active_exemptions = [
            exemption for exemption in candidates
            if exemption.is_active(now)
        ]
        
        return active_exemptions
    
    def get_exemptions_by_jira(self, ticket_id: str) -> List[TimeWindowExemption]:
        """Get exemptions associated with a JIRA ticket"""
        return [
            exemption for exemption in self.exemptions.values()
            if ticket_id in exemption.jira_tickets
        ]
    
    def delay_escalation(
        self,
        anomaly: Any,
        fingerprint: str,
        exemption: TimeWindowExemption,
        original_time: datetime,
        escalation_level: str,
        stakeholders: List[str]
    ) -> str:
        """Schedule a delayed escalation"""
        # Calculate scheduled time
        if exemption.action != ExemptionAction.DELAY:
            raise ValueError("Exemption action must be DELAY")
            
        scheduled_time = original_time + timedelta(minutes=exemption.delay_minutes)
        
        # If exemption ends before delay completes, schedule for exemption end
        if exemption.end_time and scheduled_time > exemption.end_time:
            scheduled_time = exemption.end_time + timedelta(minutes=1)
            
        # Create delayed escalation record
        delayed = DelayedEscalation(
            anomaly_fingerprint=fingerprint,
            cluster_id=getattr(anomaly, 'cluster_id', None),
            exemption_id=exemption.id,
            original_time=original_time,
            scheduled_time=scheduled_time,
            escalation_level=escalation_level,
            stakeholders=stakeholders,
            service=getattr(anomaly, 'service_name', ''),
            anomaly_type=getattr(anomaly, 'anomaly_type', '').name if hasattr(getattr(anomaly, 'anomaly_type', None), 'name') else str(getattr(anomaly, 'anomaly_type', ''))
        )
        
        self.delayed_escalations[delayed.id] = delayed
        
        # Update exemption usage
        exemption.applied_count += 1
        exemption.last_applied = datetime.now()
        
        return delayed.id
    
    def add_to_batch(
        self,
        anomaly: Any,
        fingerprint: str,
        exemption: TimeWindowExemption,
        stakeholder_id: str
    ) -> str:
        """Add an alert to a batch for later delivery"""
        if exemption.action != ExemptionAction.BATCH:
            raise ValueError("Exemption action must be BATCH")
            
        # Find or create batch for this stakeholder and exemption
        batch_key = f"{exemption.id}:{stakeholder_id}"
        
        if batch_key in self.batched_alerts:
            # Add to existing batch
            batch = self.batched_alerts[batch_key]
        else:
            # Create new batch
            next_delivery = datetime.now() + timedelta(minutes=exemption.batch_minutes)
            
            # If exemption ends before next delivery, schedule for exemption end
            if exemption.end_time and next_delivery > exemption.end_time:
                next_delivery = exemption.end_time
                
            batch = BatchedAlerts(
                exemption_id=exemption.id,
                stakeholder_id=stakeholder_id,
                scheduled_delivery=next_delivery
            )
            self.batched_alerts[batch_key] = batch
            
        # Add alert to batch
        alert_data = {
            "fingerprint": fingerprint,
            "timestamp": datetime.now(),
            "service": getattr(anomaly, 'service_name', ''),
            "anomaly_type": getattr(anomaly, 'anomaly_type', '').name if hasattr(getattr(anomaly, 'anomaly_type', None), 'name') else str(getattr(anomaly, 'anomaly_type', ''))
        }
        
        batch.add_alert(alert_data)
        
        # Update exemption usage
        exemption.applied_count += 1
        exemption.last_applied = datetime.now()
        
        return batch.id
    
    def get_due_delayed_escalations(self, current_time: Optional[datetime] = None) -> List[DelayedEscalation]:
        """Get delayed escalations that are now due"""
        now = current_time or datetime.now()
        
        due_escalations = [
            delayed for delayed in self.delayed_escalations.values()
            if not delayed.executed and delayed.scheduled_time <= now
        ]
        
        return due_escalations
    
    def get_due_batched_alerts(self, current_time: Optional[datetime] = None) -> List[BatchedAlerts]:
        """Get batched alerts that are due for delivery"""
        now = current_time or datetime.now()
        
        due_batches = [
            batch for batch in self.batched_alerts.values()
            if not batch.delivered and batch.scheduled_delivery <= now
        ]
        
        return due_batches
    
    def mark_delayed_escalation_executed(self, delayed_id: str) -> bool:
        """Mark a delayed escalation as executed"""
        if delayed_id not in self.delayed_escalations:
            return False
            
        delayed = self.delayed_escalations[delayed_id]
        delayed.executed = True
        delayed.execution_time = datetime.now()
        
        return True
    
    def mark_batch_delivered(self, batch_id: str) -> bool:
        """Mark a batch as delivered"""
        for key, batch in self.batched_alerts.items():
            if batch.id == batch_id:
                batch.delivered = True
                return True
                
        return False
    
    def get_exemptions_by_type(self, exemption_type: ExemptionType) -> List[TimeWindowExemption]:
        """Get all exemptions of a specific type"""
        tag = f"type:{exemption_type.name}"
        
        if tag not in self.exemption_tags:
            return []
            
        return [
            self.exemptions[ex_id]
            for ex_id in self.exemption_tags[tag]
            if ex_id in self.exemptions
        ]
    
    def create_maintenance_window(
        self,
        name: str,
        start_time: datetime,
        end_time: datetime,
        services: List[str],
        creator: str,
        action: ExemptionAction = ExemptionAction.DELAY,
        delay_minutes: int = 30,
        jira_ticket: Optional[str] = None
    ) -> TimeWindowExemption:
        """Helper to create a maintenance window exemption"""
        exemption = TimeWindowExemption(
            name=name,
            description=f"Maintenance window for {', '.join(services)}",
            exemption_type=ExemptionType.MAINTENANCE,
            action=action,
            start_time=start_time,
            end_time=end_time,
            timezone="UTC",  # Default, can be changed
            recurrence=RecurrenceType.ONCE,
            services=services,
            delay_minutes=delay_minutes,
            created_by=creator,
            created_at=datetime.now()
        )
        
        if jira_ticket:
            exemption.jira_tickets = [jira_ticket]
            
        self.add_exemption(exemption)
        return exemption
    
    def create_deploy_window(
        self,
        name: str,
        start_time: datetime,
        end_time: datetime,
        services: List[str],
        environments: List[str],
        creator: str,
        action: ExemptionAction = ExemptionAction.DOWNGRADE,
        jira_ticket: Optional[str] = None
    ) -> TimeWindowExemption:
        """Helper to create a deployment window exemption"""
        exemption = TimeWindowExemption(
            name=name,
            description=f"Deployment window for {', '.join(services)}",
            exemption_type=ExemptionType.DEPLOY,
            action=action,
            start_time=start_time,
            end_time=end_time,
            timezone="UTC",  # Default, can be changed
            recurrence=RecurrenceType.ONCE,
            services=services,
            environments=environments,
            created_by=creator,
            created_at=datetime.now()
        )
        
        if jira_ticket:
            exemption.jira_tickets = [jira_ticket]
            
        self.add_exemption(exemption)
        return exemption

class ExemptionAwareEscalationEngine:
    """Enhanced escalation engine that respects time window exemptions"""
    
    def __init__(
        self, 
        base_engine,  # Could be TemporallyAwareEscalationEngine or similar
        exemption_manager: TimeWindowExemptionManager
    ):
        self.base_engine = base_engine
        self.exemptions = exemption_manager
        
    async def process_anomaly(self, anomaly: Any) -> Dict:
        """Process an anomaly with exemption awareness"""
        # Record original anomaly details for tracing
        is_exempt = False
        applied_exemptions = []
        
        # Check for active exemptions that apply to this anomaly
        active_exemptions = self.exemptions.get_active_exemptions(
            service=getattr(anomaly, 'service_name', None),
            environment=getattr(anomaly, 'environment', None),
            anomaly_type=getattr(anomaly, 'anomaly_type', None)
        )
        
        # Filter exemptions based on anomaly criticality
        if hasattr(anomaly, 'service_criticality') and active_exemptions:
            criticality = anomaly.service_criticality
            if hasattr(criticality, 'name'):
                criticality_name = criticality.name
            else:
                criticality_name = str(criticality)
                
            filtered_exemptions = []
            for ex in active_exemptions:
                if not ex.max_criticality or criticality_name <= ex.max_criticality:
                    filtered_exemptions.append(ex)
                    
            active_exemptions = filtered_exemptions
            
        if active_exemptions:
            is_exempt = True
            
            # Use the highest precedence exemption
            # Precedence order: MAINTENANCE > DEPLOY > INCIDENT > FREEZE > LOAD_TEST > QUIET_HOURS > HOLIDAY > CUSTOMIZED
            # Or use custom precedence logic as needed
            exemption_precedence = {
                ExemptionType.MAINTENANCE: 0,
                ExemptionType.DEPLOY: 1,
                ExemptionType.INCIDENT: 2,
                ExemptionType.FREEZE: 3,
                ExemptionType.LOAD_TEST: 4,
                ExemptionType.QUIET_HOURS: 5,
                ExemptionType.HOLIDAY: 6,
                ExemptionType.CUSTOMIZED: 7
            }
            
            active_exemptions.sort(key=lambda ex: exemption_precedence.get(ex.exemption_type, 99))
            primary_exemption = active_exemptions[0]
            applied_exemptions = [ex.id for ex in active_exemptions]
            
            # Apply exemption action
            action = primary_exemption.action
            
            # Add exemption information to anomaly for tracking
            anomaly.details = getattr(anomaly, 'details', {})
            anomaly.details.update({
                "exemption_applied": primary_exemption.id,
                "exemption_name": primary_exemption.name,
                "exemption_type": primary_exemption.exemption_type.name,
                "exemption_action": action.name
            })
            
            # Handle based on action type
            if action == ExemptionAction.SUPPRESS:
                # Don't process the anomaly at all
                return {
                    "status": "suppressed",
                    "reason": "time_window_exemption",
                    "exemption": primary_exemption.to_dict(),
                    "fingerprint": getattr(anomaly, 'fingerprint', None)
                }
                
            elif action == ExemptionAction.DELAY:
                # Queue the anomaly for delayed processing
                result = await self.base_engine.queue_anomaly_for_evaluation(anomaly)
                
                # Get stakeholders who would be notified
                stakeholders = result.get("stakeholders_notified", [])
                
                # Create delayed escalation
                delayed_id = self.exemptions.delay_escalation(
                    anomaly,
                    anomaly.fingerprint,
                    primary_exemption,
                    datetime.now(),
                    result.get("escalation_level", "INITIAL"),
                    stakeholders
                )
                
                return {
                    "status": "delayed",
                    "delayed_id": delayed_id,
                    "original_result": result,
                    "scheduled_time": self.exemptions.delayed_escalations[delayed_id].scheduled_time,
                    "exemption": primary_exemption.to_dict()
                }
                
            elif action == ExemptionAction.DOWNGRADE:
                # Modify the anomaly to reduce its severity/urgency
                # This is one approach - alternatively, could modify the risk score calculation
                if hasattr(anomaly, 'service_criticality'):
                    original_criticality = anomaly.service_criticality
                    # Downgrade by one level if possible
                    if hasattr(anomaly.service_criticality, 'value'):
                        # Enum-based criticality
                        criticality_type = type(anomaly.service_criticality)
                        criticality_values = list(criticality_type)
                        current_idx = criticality_values.index(anomaly.service_criticality)
                        if current_idx < len(criticality_values) - 1:
                            anomaly.service_criticality = criticality_values[current_idx + 1]
                    
                    # Record the downgrade
                    anomaly.details["original_criticality"] = original_criticality.name if hasattr(original_criticality, 'name') else str(original_criticality)
                    anomaly.details["downgraded_to"] = anomaly.service_criticality.name if hasattr(anomaly.service_criticality, 'name') else str(anomaly.service_criticality)
                
                # Continue with normal processing
                result = await self.base_engine.queue_anomaly_for_evaluation(anomaly)
                
                return {
                    "status": "downgraded",
                    "result": result,
                    "exemption": primary_exemption.to_dict()
                }
                
            elif action == ExemptionAction.REDIRECT:
                # Modify stakeholders to use alternatives
                result = await self.base_engine.queue_anomaly_for_evaluation(anomaly)
                
                # If we have alternative stakeholders defined, override the normal routing
                if primary_exemption.alternative_stakeholders:
                    # This is a simplified version - actual implementation would depend 
                    # on your notification system and how stakeholders are managed
                    return {
                        "status": "redirected",
                        "result": result,
                        "original_stakeholders": result.get("stakeholders_notified", []),
                        "redirected_to": primary_exemption.alternative_stakeholders,
                        "exemption": primary_exemption.to_dict()
                    }
                    
                return {
                    "status": "processed",
                    "result": result,
                    "exemption": primary_exemption.to_dict()
                }
                
            elif action == ExemptionAction.BATCH:
                # Queue the anomaly but add to batch for delivery
                result = await self.base_engine.queue_anomaly_for_evaluation(anomaly)
                
                # Get stakeholders who would be notified
                stakeholders = result.get("stakeholders_notified", [])
                
                # Add to batch for each stakeholder
                batch_ids = []
                for stakeholder_id in stakeholders:
                    batch_id = self.exemptions.add_to_batch(
                        anomaly,
                        anomaly.fingerprint,
                        primary_exemption,
                        stakeholder_id
                    )
                    batch_ids.append(batch_id)
                
                return {
                    "status": "batched",
                    "batch_ids": batch_ids,
                    "original_result": result,
                    "exemption": primary_exemption.to_dict()
                }
                
            elif action == ExemptionAction.LOG_ONLY:
                # Just log without notification
                # Still run evaluation to record the anomaly
                result = await self.base_engine.queue_anomaly_for_evaluation(anomaly)
                
                return {
                    "status": "logged_only",
                    "result": result,
                    "exemption": primary_exemption.to_dict()
                }
        
        # No exemption applies - process normally
        result = await self.base_engine.queue_anomaly_for_evaluation(anomaly)
        
        return {
            "status": "processed",
            "result": result,
            "is_exempt": is_exempt,
            "applied_exemptions": applied_exemptions
        }
        
    async def process_delayed_escalations(self) -> List[Dict]:
        """Process any delayed escalations that are now due"""
        # Get due delayed escalations
        due_delays = self.exemptions.get_due_delayed_escalations()
        
        if not due_delays:
            return []
            
        results = []
        for delayed in due_delays:
            # Get the anomaly if it still exists
            anomaly = None
            if delayed.anomaly_fingerprint in self.base_engine.alert_tracker.alerts:
                alert = self.base_engine.alert_tracker.alerts[delayed.anomaly_fingerprint]
                anomaly = alert["last_anomaly"]
                
            if not anomaly:
                # Anomaly no longer exists or was resolved
                self.exemptions.mark_delayed_escalation_executed(delayed.id)
                results.append({
                    "status": "skipped",
                    "reason": "anomaly_not_found",
                    "delayed_id": delayed.id,
                    "fingerprint": delayed.anomaly_fingerprint
                })
                continue
                
            # Check if already escalated beyond our level
            if delayed.anomaly_fingerprint in self.base_engine.alert_tracker.alerts:
                current_level = self.base_engine.alert_tracker.alerts[delayed.anomaly_fingerprint].get(
                    "current_escalation_level")
                    
                if current_level and current_level.name > delayed.escalation_level:
                    # Already escalated beyond this level
                    self.exemptions.mark_delayed_escalation_executed(delayed.id)
                    results.append({
                        "status": "skipped",
                        "reason": "already_escalated",
                        "delayed_id": delayed.id,
                        "fingerprint": delayed.anomaly_fingerprint,
                        "current_level": current_level.name,
                        "delayed_level": delayed.escalation_level
                    })
                    continue
            
            # Process the escalation now
            try:
                # Add delayed execution info to anomaly
                anomaly.details["delayed_execution"] = True
                anomaly.details["original_time"] = delayed.original_time.isoformat()
                anomaly.details["delay_minutes"] = (datetime.now() - delayed.original_time).total_seconds() / 60
                
                # Process the escalation (implementation depends on your escalation engine)
                # This is a simplified example
                escalation_result = await self.base_engine.escalate_anomaly(
                    anomaly, delayed.escalation_level)
                
                self.exemptions.mark_delayed_escalation_executed(delayed.id)
                
                results.append({
                    "status": "executed",
                    "delayed_id": delayed.id,
                    "fingerprint": delayed.anomaly_fingerprint,
                    "result": escalation_result
                })
            except Exception as e:
                results.append({
                    "status": "error",
                    "delayed_id": delayed.id,
                    "fingerprint": delayed.anomaly_fingerprint,
                    "error": str(e)
                })
                
        return results
        
    async def process_batched_alerts(self) -> List[Dict]:
        """Process any batched alerts that are now due for delivery"""
        # Get due batches
        due_batches = self.exemptions.get_due_batched_alerts()
        
        if not due_batches:
            return []
            
        results = []
        for batch in due_batches:
            try:
                # Get stakeholder
                stakeholder = self._get_stakeholder(batch.stakeholder_id)
                
                if not stakeholder:
                    # Stakeholder no longer exists
                    self.exemptions.mark_batch_delivered(batch.id)
                    results.append({
                        "status": "skipped",
                        "reason": "stakeholder_not_found",
                        "batch_id": batch.id,
                        "stakeholder_id": batch.stakeholder_id
                    })
                    continue
                
                # Create batch notification
                summary = batch.get_summary()
                
                # This would call your notification system
                # notification_result = await self.send_batch_notification(stakeholder, summary, batch.alerts)
                notification_result = {"status": "sent"}  # Placeholder
                
                self.exemptions.mark_batch_delivered(batch.id)
                
                results.append({
                    "status": "delivered",
                    "batch_id": batch.id,
                    "stakeholder_id": batch.stakeholder_id,
                    "alert_count": len(batch.alerts),
                    "notification_result": notification_result
                })
            except Exception as e:
                results.append({
                    "status": "error",
                    "batch_id": batch.id,
                    "stakeholder_id": batch.stakeholder_id,
                    "error": str(e)
                })
                
        return results
        
    def _get_stakeholder(self, stakeholder_id: str) -> Any:
        """Get a stakeholder by ID"""
        # This is a placeholder - implementation depends on your system
        registry = getattr(self.base_engine, 'stakeholder_registry', None)
        if not registry:
            return None
            
        # Assuming stakeholder_registry.get_stakeholder() exists
        return registry.get_stakeholder(stakeholder_id)

class RecurringScheduleManager:
    """Manages complex recurring schedules for time window exemptions"""
    
    def __init__(self):
        self.schedule_templates: Dict[str, Dict] = {}
        
    def create_schedule(self, name: str, schedule_type: str = "cron") -> str:
        """Create a new schedule template"""
        schedule_id = str(uuid.uuid4())
        
        template = {
            "id": schedule_id,
            "name": name,
            "type": schedule_type,
            "definition": {},
            "created_at": datetime.now()
        }
        
        self.schedule_templates[schedule_id] = template
        return schedule_id
    
    def define_cron_schedule(
        self, 
        schedule_id: str,
        minute: str = "*",
        hour: str = "*",
        day: str = "*",
        month: str = "*",
        weekday: str = "*"
    ) -> bool:
        """Define a schedule using cron-like syntax"""
        if schedule_id not in self.schedule_templates:
            return False
            
        template = self.schedule_templates[schedule_id]
        if template["type"] != "cron":
            return False
            
        template["definition"] = {
            "minute": minute,
            "hour": hour,
            "day": day,
            "month": month,
            "weekday": weekday
        }
        
        return True
    
    def is_active(self, schedule_id: str, current_time: Optional[datetime] = None) -> bool:
        """Check if a schedule is currently active"""
        if schedule_id not in self.schedule_templates:
            return False
            
        now = current_time or datetime.now()
        template = self.schedule_templates[schedule_id]
        
        if template["type"] == "cron":
            return self._check_cron_match(template["definition"], now)
            
        return False
    
    def _check_cron_match(self, cron_def: Dict, dt: datetime) -> bool:
        """Check if a datetime matches a cron definition"""
        # Extract components
        minute = str(dt.minute)
        hour = str(dt.hour)
        day = str(dt.day)
        month = str(dt.month)
        weekday = str(dt.weekday())
        
        # Helper to check if a value matches a cron pattern
        def matches(value, pattern):
            if pattern == "*":
                return True
                
            # Handle comma-separated values
            if "," in pattern:
                return value in pattern.split(",")
                
            # Handle ranges
            if "-" in pattern:
                start, end = pattern.split("-")
                return int(start) <= int(value) <= int(end)
                
            # Handle steps
            if "/" in pattern:
                base, step = pattern.split("/")
                if base == "*":
                    return int(value) % int(step) == 0
                    
            # Direct match
            return value == pattern
            
        # Check all components
        return (
            matches(minute, cron_def.get("minute", "*")) and
            matches(hour, cron_def.get("hour", "*")) and
            matches(day, cron_def.get("day", "*")) and
            matches(month, cron_def.get("month", "*")) and
            matches(weekday, cron_def.get("weekday", "*"))
        )
    
    def generate_next_occurrences(
        self, 
        schedule_id: str, 
        count: int = 5,
        start_time: Optional[datetime] = None
    ) -> List[datetime]:
        """Generate the next occurrences of a schedule"""
        if schedule_id not in self.schedule_templates:
            return []
            
        template = self.schedule_templates[schedule_id]
        start = start_time or datetime.now()
        
        if template["type"] == "cron":
            return self._generate_cron_occurrences(template["definition"], start, count)
            
        return []
    
    def _generate_cron_occurrences(self, cron_def: Dict, start: datetime, count: int) -> List[datetime]:
        """Generate upcoming occurrences for a cron schedule"""
        # This is a simplified implementation - a real one would be more complex
        occurrences = []
        current = start
        
        # Try consecutive minutes until we find enough matches
        # Real implementation would use more efficient algorithms
        while len(occurrences) < count:
            current += timedelta(minutes=1)
            if self._check_cron_match(cron_def, current):
                occurrences.append(current)
                
        return occurrences
    
    def apply_schedule_to_exemption(
        self,
        schedule_id: str,
        exemption: TimeWindowExemption,
        window_duration_minutes: int = 60
    ) -> bool:
        """Apply a schedule to an exemption for complex recurrence"""
        if schedule_id not in self.schedule_templates:
            return False
            
        # Create a custom recurrence with the schedule ID
        exemption.recurrence = RecurrenceType.CUSTOM
        
        # Store schedule reference in the exemption
        if not hasattr(exemption, "custom_schedule"):
            exemption.custom_schedule = {}
        
        exemption.custom_schedule = {
            "id": schedule_id,
            "window_duration": window_duration_minutes
        }
        
        return True