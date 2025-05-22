from datetime import datetime, timedelta
from enum import Enum, auto
from typing import Dict, List, Set, Optional, Tuple, Union, Callable, Any
from dataclasses import dataclass
import uuid

# Alert lifecycle states
class AlertState(Enum):
    NEW = auto()
    ACKNOWLEDGED = auto()
    IN_PROGRESS = auto()
    RESOLVED = auto()
    ESCALATED = auto()
    SUPPRESSED = auto()

# Escalation level definitions
class EscalationLevel(Enum):
    INITIAL = 0      # First notification to direct owners
    TEAM_WIDE = 1    # Broader team notification
    MANAGEMENT = 2   # Team leads and managers
    INCIDENT = 3     # Incident response process
    EXECUTIVE = 4    # Executive notification

@dataclass
class EscalationRule:
    """Definition of when and how to escalate an alert"""
    name: str
    id: str = None
    # Time thresholds
    time_to_escalate: timedelta  # Time before escalating if no acknowledgment
    resolution_sla: Optional[timedelta] = None  # Time allowed for resolution before next escalation
    
    # Who to notify at this escalation level
    target_roles: List[str] = None
    target_teams: List[str] = None
    additional_stakeholders: List[str] = None  # Specific stakeholder IDs
    
    # Conditions
    min_severity: Optional[AlertUrgency] = None  # Minimum severity to apply this rule
    service_criticality: Optional[List[ServiceCriticality]] = None
    anomaly_types: Optional[List[AnomalyType]] = None
    
    # Escalation behavior
    next_level: Optional[EscalationLevel] = None  # Next level if this escalation fails
    notification_channels: List[NotificationChannel] = None  # Override default channels
    
    # Special handling
    create_incident: bool = False  # Should this escalation create an incident
    suppress_duplicates: bool = False  # Suppress similar alerts during this escalation
    
    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
        self.target_roles = self.target_roles or []
        self.target_teams = self.target_teams or []
        self.additional_stakeholders = self.additional_stakeholders or []
        self.notification_channels = self.notification_channels or []

class AlertTracker:
    """Tracks the state of alerts through their lifecycle"""
    
    def __init__(self):
        self.alerts: Dict[str, Dict] = {}  # fingerprint -> alert state
        self.acknowledgments: Dict[str, List[Dict]] = {}  # fingerprint -> ack records
        self.escalations: Dict[str, List[Dict]] = {}  # fingerprint -> escalation records
        self.current_incidents: Dict[str, str] = {}  # fingerprint -> incident ID
    
    def register_alert(self, anomaly: Anomaly, routing_result: Dict) -> str:
        """Register a new alert or update existing one"""
        fingerprint = anomaly.fingerprint
        
        if fingerprint in self.alerts:
            # Update existing alert
            alert_record = self.alerts[fingerprint]
            alert_record["last_seen"] = datetime.now()
            alert_record["count"] += 1
            alert_record["last_anomaly"] = anomaly
            return fingerprint
        
        # Create new alert record
        self.alerts[fingerprint] = {
            "first_seen": datetime.now(),
            "last_seen": datetime.now(),
            "count": 1,
            "state": AlertState.NEW,
            "current_escalation_level": EscalationLevel.INITIAL,
            "last_escalation_time": None,
            "service_name": anomaly.service_name,
            "service_criticality": anomaly.service_criticality,
            "anomaly_type": anomaly.anomaly_type,
            "confidence": anomaly.confidence,
            "last_anomaly": anomaly,
            "stakeholders_notified": routing_result.get("stakeholders_notified", [])
        }
        
        # Initialize records
        self.acknowledgments[fingerprint] = []
        self.escalations[fingerprint] = []
        
        return fingerprint
    
    def acknowledge_alert(self, fingerprint: str, 
                         stakeholder_id: str, 
                         notes: str = None) -> bool:
        """Record an acknowledgment for an alert"""
        if fingerprint not in self.alerts:
            return False
        
        alert = self.alerts[fingerprint]
        
        # Record acknowledgment
        ack_record = {
            "timestamp": datetime.now(),
            "stakeholder_id": stakeholder_id,
            "notes": notes,
        }
        self.acknowledgments[fingerprint].append(ack_record)
        
        # Update alert state
        if alert["state"] == AlertState.NEW:
            alert["state"] = AlertState.ACKNOWLEDGED
            
        return True
    
    def resolve_alert(self, fingerprint: str, 
                     stakeholder_id: str,
                     resolution_notes: str = None) -> bool:
        """Mark an alert as resolved"""
        if fingerprint not in self.alerts:
            return False
            
        alert = self.alerts[fingerprint]
        alert["state"] = AlertState.RESOLVED
        alert["resolution_time"] = datetime.now()
        alert["resolved_by"] = stakeholder_id
        alert["resolution_notes"] = resolution_notes
        
        # If this alert was part of an incident, update that too
        if fingerprint in self.current_incidents:
            incident_id = self.current_incidents[fingerprint]
            # Incident resolution logic would go here
            # This could trigger a separate incident resolution workflow
            
        return True
    
    def record_escalation(self, fingerprint: str, 
                         level: EscalationLevel,
                         notified_stakeholders: List[str],
                         rule_id: str) -> None:
        """Record an escalation event"""
        if fingerprint not in self.alerts:
            return
            
        alert = self.alerts[fingerprint]
        
        # Update alert record
        alert["state"] = AlertState.ESCALATED
        alert["current_escalation_level"] = level
        alert["last_escalation_time"] = datetime.now()
        
        # Add escalation record
        escalation_record = {
            "timestamp": datetime.now(),
            "level": level,
            "notified_stakeholders": notified_stakeholders,
            "rule_id": rule_id
        }
        self.escalations[fingerprint].append(escalation_record)
    
    def get_unresolved_alerts(self, 
                             older_than: Optional[timedelta] = None,
                             service: Optional[str] = None) -> List[str]:
        """Get fingerprints of unresolved alerts, optionally filtered"""
        unresolved = []
        now = datetime.now()
        
        for fp, alert in self.alerts.items():
            if alert["state"] in [AlertState.NEW, AlertState.ACKNOWLEDGED, 
                                 AlertState.ESCALATED, AlertState.IN_PROGRESS]:
                if service and alert["service_name"] != service:
                    continue
                    
                if older_than:
                    time_since_last_update = now - alert["last_seen"]
                    if time_since_last_update < older_than:
                        continue
                        
                unresolved.append(fp)
                
        return unresolved
    
    def suppress_alert(self, fingerprint: str, 
                      duration: timedelta,
                      stakeholder_id: str,
                      reason: str = None) -> bool:
        """Suppress an alert for a specified duration"""
        if fingerprint not in self.alerts:
            return False
            
        alert = self.alerts[fingerprint]
        alert["state"] = AlertState.SUPPRESSED
        alert["suppression_start"] = datetime.now()
        alert["suppression_end"] = datetime.now() + duration
        alert["suppressed_by"] = stakeholder_id
        alert["suppression_reason"] = reason
        
        return True
    
    def is_suppressed(self, fingerprint: str) -> bool:
        """Check if an alert is currently suppressed"""
        if fingerprint not in self.alerts:
            return False
            
        alert = self.alerts[fingerprint]
        if alert["state"] != AlertState.SUPPRESSED:
            return False
            
        now = datetime.now()
        return now < alert.get("suppression_end", now)

class IncidentManager:
    """Manages incidents created from escalated alerts"""
    
    def __init__(self, stakeholder_registry: StakeholderRegistry):
        self.stakeholder_registry = stakeholder_registry
        self.incidents: Dict[str, Dict] = {}
        self.incident_commanders: Dict[str, List[str]] = {}  # team -> commanders
    
    def register_incident_commander(self, team: str, stakeholder_id: str) -> None:
        """Register a stakeholder as an incident commander for a team"""
        if team not in self.incident_commanders:
            self.incident_commanders[team] = []
        self.incident_commanders[team].append(stakeholder_id)
    
    def create_incident(self, 
                       anomaly: Anomaly, 
                       fingerprint: str,
                       escalation_level: EscalationLevel) -> str:
        """Create a new incident from an alert"""
        # Generate incident ID
        incident_id = f"INC-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8]}"
        
        # Find an available incident commander
        team = self._get_responsible_team(anomaly.service_name)
        ic_id = self._get_available_incident_commander(team)
        
        # Create incident record
        self.incidents[incident_id] = {
            "id": incident_id,
            "created_at": datetime.now(),
            "source_anomaly": anomaly.fingerprint,
            "service_name": anomaly.service_name,
            "criticality": anomaly.service_criticality,
            "anomaly_type": anomaly.anomaly_type,
            "status": "ACTIVE",
            "incident_commander": ic_id,
            "team": team,
            "related_alerts": [fingerprint]
        }
        
        return incident_id
    
    def _get_responsible_team(self, service_name: str) -> str:
        """Determine which team is responsible for a service"""
        # This would be implemented based on your service catalog
        # For now, returning a placeholder
        return "sre"
    
    def _get_available_incident_commander(self, team: str) -> Optional[str]:
        """Find an available incident commander for the specified team"""
        if team not in self.incident_commanders:
            return None
            
        on_call = self.stakeholder_registry.get_on_call(f"{team}-ic")
        if on_call:
            return on_call[0].id
            
        # Fallback to any registered IC
        for ic_id in self.incident_commanders[team]:
            stakeholder = next((s for s in self.stakeholder_registry.stakeholders 
                             if s.id == ic_id and s.is_available()), None)
            if stakeholder:
                return stakeholder.id
                
        return None

class EscalationPolicyEngine:
    """Manages and executes escalation policies for alerts"""
    
    def __init__(
        self,
        stakeholder_registry: StakeholderRegistry,
        notification_gateway: NotificationGateway,
        alert_tracker: AlertTracker,
        incident_manager: IncidentManager
    ):
        self.stakeholder_registry = stakeholder_registry
        self.notification_gateway = notification_gateway
        self.alert_tracker = alert_tracker
        self.incident_manager = incident_manager
        self.rules_by_level: Dict[EscalationLevel, List[EscalationRule]] = {
            level: [] for level in EscalationLevel
        }
        self.service_specific_rules: Dict[str, List[EscalationRule]] = {}
    
    def add_rule(self, rule: EscalationRule, service: Optional[str] = None) -> None:
        """Add an escalation rule, optionally for a specific service"""
        if service:
            if service not in self.service_specific_rules:
                self.service_specific_rules[service] = []
            self.service_specific_rules[service].append(rule)
        else:
            level = EscalationLevel.INITIAL
            if rule.next_level:
                level = rule.next_level
            self.rules_by_level[level].append(rule)
    
    def get_applicable_rules(self, 
                           anomaly: Anomaly, 
                           current_level: EscalationLevel) -> List[EscalationRule]:
        """Get rules that apply to this anomaly at its current escalation level"""
        # Check service-specific rules first
        applicable_rules = []
        
        service_rules = self.service_specific_rules.get(anomaly.service_name, [])
        for rule in service_rules:
            if self._rule_applies(rule, anomaly, current_level):
                applicable_rules.append(rule)
                
        # If no service-specific rules, use general rules
        if not applicable_rules:
            for rule in self.rules_by_level[current_level]:
                if self._rule_applies(rule, anomaly, current_level):
                    applicable_rules.append(rule)
                    
        return applicable_rules
    
    def _rule_applies(self, 
                     rule: EscalationRule, 
                     anomaly: Anomaly, 
                     current_level: EscalationLevel) -> bool:
        """Check if a rule applies to this anomaly"""
        # Check service criticality
        if (rule.service_criticality and 
            anomaly.service_criticality not in rule.service_criticality):
            return False
            
        # Check anomaly type
        if rule.anomaly_types and anomaly.anomaly_type not in rule.anomaly_types:
            return False
            
        # Additional checks could be added here
        
        return True
    
    async def check_for_escalations(self) -> List[Dict]:
        """
        Scan for alerts that need escalation based on time thresholds
        This would typically be called by a scheduled task
        """
        now = datetime.now()
        escalation_actions = []
        
        # Get all unresolved alerts
        unresolved = self.alert_tracker.get_unresolved_alerts()
        
        for fingerprint in unresolved:
            alert = self.alert_tracker.alerts[fingerprint]
            
            # Skip suppressed alerts
            if self.alert_tracker.is_suppressed(fingerprint):
                continue
                
            # Get the anomaly and current escalation level
            anomaly = alert["last_anomaly"]
            current_level = alert["current_escalation_level"]
            
            # Get applicable rules for this alert
            rules = self.get_applicable_rules(anomaly, current_level)
            if not rules:
                continue
                
            # Use the first applicable rule
            rule = rules[0]
            
            # Check if it's time to escalate
            last_update = alert.get("last_escalation_time", alert["first_seen"])
            time_since_update = now - last_update
            
            if time_since_update < rule.time_to_escalate:
                continue
                
            # Time to escalate!
            escalation = await self._perform_escalation(fingerprint, anomaly, rule)
            if escalation:
                escalation_actions.append(escalation)
                
        return escalation_actions
    
    async def _perform_escalation(self, 
                                fingerprint: str, 
                                anomaly: Anomaly, 
                                rule: EscalationRule) -> Dict:
        """Execute an escalation based on the rule"""
        # Determine who to notify
        stakeholders = []
        
        # Add stakeholders by role
        for role in rule.target_roles:
            role_stakeholders = [s for s in self.stakeholder_registry.stakeholders 
                              if role.lower() in s.role.lower() and s.is_available()]
            stakeholders.extend(role_stakeholders)
            
        # Add stakeholders by team
        for team in rule.target_teams:
            team_stakeholders = self.stakeholder_registry.get_on_call(team)
            stakeholders.extend(team_stakeholders)
            
        # Add specific stakeholders
        for stakeholder_id in rule.additional_stakeholders:
            stakeholder = next((s for s in self.stakeholder_registry.stakeholders 
                             if s.id == stakeholder_id and s.is_available()), None)
            if stakeholder:
                stakeholders.append(stakeholder)
                
        # Remove duplicates
        stakeholders = list(set(stakeholders))
        
        # Create an incident if required
        incident_id = None
        if rule.create_incident:
            incident_id = self.incident_manager.create_incident(
                anomaly, fingerprint, rule.next_level
            )
            
        # Send notifications
        notified_ids = []
        for stakeholder in stakeholders:
            # Determine urgency
            urgency = AlertUrgency.HIGH  # Default for escalations
            if rule.next_level == EscalationLevel.EXECUTIVE:
                urgency = AlertUrgency.CRITICAL
                
            # Create escalation message
            escalation_details = {
                "is_escalation": True,
                "escalation_level": rule.next_level,
                "previous_notifications": self.alert_tracker.alerts[fingerprint]["stakeholders_notified"],
                "alert_age": datetime.now() - self.alert_tracker.alerts[fingerprint]["first_seen"],
                "alert_count": self.alert_tracker.alerts[fingerprint]["count"],
                "incident_id": incident_id
            }
            
            # Update the anomaly details with escalation info
            anomaly.details.update(escalation_details)
            
            # Send via preferred channels or rule-specified channels
            channels = rule.notification_channels or stakeholder.notification_preferences.get(urgency, [])
            for channel in channels:
                if channel in self.notification_gateway.adapters:
                    adapter = self.notification_gateway.adapters[channel]
                    await adapter.send_notification(stakeholder, anomaly, urgency)
                    
            notified_ids.append(stakeholder.id)
            
        # Record the escalation
        self.alert_tracker.record_escalation(
            fingerprint, rule.next_level, notified_ids, rule.id
        )
        
        return {
            "fingerprint": fingerprint,
            "escalated_to_level": rule.next_level,
            "notified_stakeholders": notified_ids,
            "incident_created": incident_id is not None,
            "incident_id": incident_id,
            "timestamp": datetime.now()
        }
    
    def get_next_escalation_time(self, fingerprint: str) -> Optional[datetime]:
        """Determine when the next escalation will occur for an alert"""
        if fingerprint not in self.alert_tracker.alerts:
            return None
            
        alert = self.alert_tracker.alerts[fingerprint]
        
        # If resolved or suppressed, no escalation
        if alert["state"] in [AlertState.RESOLVED, AlertState.SUPPRESSED]:
            return None
            
        anomaly = alert["last_anomaly"]
        current_level = alert["current_escalation_level"]
        
        # Get applicable rules
        rules = self.get_applicable_rules(anomaly, current_level)
        if not rules:
            return None
            
        # Use the first applicable rule
        rule = rules[0]
        
        # Calculate next escalation time
        last_update = alert.get("last_escalation_time", alert["first_seen"])
        return last_update + rule.time_to_escalate