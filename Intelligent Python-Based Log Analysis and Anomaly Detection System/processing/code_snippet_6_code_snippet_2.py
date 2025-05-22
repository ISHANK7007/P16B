from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Set, Optional, Tuple, Union, Callable, Any

# Existing classes (Anomaly, ServiceCriticality, AnomalyType) would be used

class AlertUrgency(Enum):
    CRITICAL = auto()  # Immediate action required
    HIGH = auto()      # Action required within 15 minutes
    MEDIUM = auto()    # Action required within 1 hour
    LOW = auto()       # Action required within 1 day
    INFO = auto()      # For informational purposes

class NotificationChannel(Enum):
    SMS = auto()
    EMAIL = auto()
    SLACK = auto()
    PAGERDUTY = auto()
    TEAMS = auto()
    WEBHOOK = auto()
    CONSOLE = auto()

class Stakeholder:
    def __init__(
        self,
        id: str,
        name: str,
        role: str,
        notification_preferences: Dict[AlertUrgency, List[NotificationChannel]],
        services: List[str] = None,
        availability_hours: Dict[str, Tuple[datetime, datetime]] = None
    ):
        self.id = id
        self.name = name
        self.role = role
        self.notification_preferences = notification_preferences
        self.services = services or []
        self.availability_hours = availability_hours or {}
        
    def is_available(self, current_time: datetime = None) -> bool:
        """Check if stakeholder is available based on current time"""
        # Implementation details
        pass

class RiskScorer:
    """Calculates risk scores for anomalies"""
    
    def __init__(
        self, 
        criticality_weights: Dict[ServiceCriticality, float] = None,
        anomaly_type_weights: Dict[AnomalyType, float] = None,
        confidence_threshold: float = 0.5
    ):
        # Default weights if none provided
        self.criticality_weights = criticality_weights or {
            ServiceCriticality.CRITICAL: 1.0,
            ServiceCriticality.HIGH: 0.75,
            ServiceCriticality.MEDIUM: 0.5,
            ServiceCriticality.LOW: 0.25
        }
        
        self.anomaly_type_weights = anomaly_type_weights or {
            AnomalyType.SECURITY: 1.0,
            AnomalyType.AVAILABILITY: 0.9,
            AnomalyType.DATA_INTEGRITY: 0.8,
            AnomalyType.PERFORMANCE: 0.7,
            AnomalyType.CONFIGURATION: 0.6
        }
        
        self.confidence_threshold = confidence_threshold
        
    def calculate_risk_score(self, anomaly: Anomaly) -> float:
        """Calculate a normalized risk score (0.0-1.0) for an anomaly"""
        if anomaly.confidence < self.confidence_threshold:
            # Reduce score for low-confidence anomalies
            confidence_factor = anomaly.confidence / self.confidence_threshold
        else:
            confidence_factor = 1.0
            
        criticality_factor = self.criticality_weights[anomaly.service_criticality]
        type_factor = self.anomaly_type_weights[anomaly.anomaly_type]
        
        # Combined score (normalized to 0.0-1.0)
        risk_score = (criticality_factor * type_factor * confidence_factor)
        return min(1.0, risk_score)
        
    def get_urgency(self, risk_score: float) -> AlertUrgency:
        """Map a risk score to an alert urgency level"""
        if risk_score >= 0.8:
            return AlertUrgency.CRITICAL
        elif risk_score >= 0.6:
            return AlertUrgency.HIGH
        elif risk_score >= 0.4:
            return AlertUrgency.MEDIUM
        elif risk_score >= 0.2:
            return AlertUrgency.LOW
        else:
            return AlertUrgency.INFO

class RoutingPolicy(ABC):
    """Abstract base class for routing policies"""
    
    @abstractmethod
    def should_route(self, anomaly: Anomaly, risk_score: float) -> bool:
        """Determine if an anomaly should be routed according to this policy"""
        pass
        
    @abstractmethod
    def get_stakeholders(self, anomaly: Anomaly, risk_score: float, 
                        all_stakeholders: List[Stakeholder]) -> List[Stakeholder]:
        """Get stakeholders who should receive this anomaly alert"""
        pass

class ServiceBasedRoutingPolicy(RoutingPolicy):
    """Routes anomalies based on service ownership"""
    
    def should_route(self, anomaly: Anomaly, risk_score: float) -> bool:
        # Always route service-based anomalies
        return True
        
    def get_stakeholders(self, anomaly: Anomaly, risk_score: float, 
                         all_stakeholders: List[Stakeholder]) -> List[Stakeholder]:
        # Find stakeholders responsible for this service
        return [s for s in all_stakeholders 
                if anomaly.service_name in s.services]

class CriticalityBasedRoutingPolicy(RoutingPolicy):
    """Routes anomalies based on service criticality"""
    
    def __init__(self, threshold: ServiceCriticality = ServiceCriticality.HIGH):
        self.threshold = threshold
        
    def should_route(self, anomaly: Anomaly, risk_score: float) -> bool:
        # Route if the service criticality meets the threshold
        criticality_levels = list(ServiceCriticality)
        return (criticality_levels.index(anomaly.service_criticality) <= 
                criticality_levels.index(self.threshold))
        
    def get_stakeholders(self, anomaly: Anomaly, risk_score: float, 
                         all_stakeholders: List[Stakeholder]) -> List[Stakeholder]:
        # For critical services, include management stakeholders
        return [s for s in all_stakeholders 
                if "manager" in s.role.lower() or "director" in s.role.lower()]

class StakeholderRegistry:
    """Manages stakeholder information and lookup"""
    
    def __init__(self):
        self.stakeholders: List[Stakeholder] = []
        self.on_call_rotations: Dict[str, List[Tuple[datetime, datetime, Stakeholder]]] = {}
        
    def add_stakeholder(self, stakeholder: Stakeholder) -> None:
        """Add a stakeholder to the registry"""
        self.stakeholders.append(stakeholder)
        
    def get_available_stakeholders(self, 
                                 service: Optional[str] = None, 
                                 role: Optional[str] = None) -> List[Stakeholder]:
        """Get stakeholders available right now, filtered by service and/or role"""
        now = datetime.now()
        available = [s for s in self.stakeholders if s.is_available(now)]
        
        if service:
            available = [s for s in available if service in s.services]
        if role:
            available = [s for s in available if role.lower() in s.role.lower()]
            
        return available
        
    def get_on_call(self, team: str, current_time: Optional[datetime] = None) -> List[Stakeholder]:
        """Get stakeholders currently on call for a specific team"""
        if team not in self.on_call_rotations:
            return []
            
        now = current_time or datetime.now()
        on_call = []
        
        for start, end, stakeholder in self.on_call_rotations[team]:
            if start <= now <= end:
                on_call.append(stakeholder)
                
        return on_call

class NotificationAdapter(ABC):
    """Abstract base class for notification channel adapters"""
    
    @abstractmethod
    async def send_notification(self, stakeholder: Stakeholder, 
                              anomaly: Anomaly, 
                              urgency: AlertUrgency) -> bool:
        """Send notification via this channel. Returns success status."""
        pass

class EmailNotificationAdapter(NotificationAdapter):
    """Email notification implementation"""
    
    async def send_notification(self, stakeholder: Stakeholder, 
                              anomaly: Anomaly, 
                              urgency: AlertUrgency) -> bool:
        # Implementation details for sending emails
        pass

# (Other notification adapters would be implemented similarly)

class NotificationGateway:
    """Manages sending notifications through various channels"""
    
    def __init__(self):
        self.adapters: Dict[NotificationChannel, NotificationAdapter] = {}
        self.notification_history: List[Dict] = []
        
    def register_adapter(self, channel: NotificationChannel, 
                        adapter: NotificationAdapter) -> None:
        """Register a notification adapter for a specific channel"""
        self.adapters[channel] = adapter
        
    async def notify_stakeholder(self, stakeholder: Stakeholder, 
                               anomaly: Anomaly, 
                               urgency: AlertUrgency) -> List[NotificationChannel]:
        """Send notifications to a stakeholder through preferred channels"""
        successful_channels = []
        channels = stakeholder.notification_preferences.get(urgency, [])
        
        for channel in channels:
            if channel in self.adapters:
                adapter = self.adapters[channel]
                success = await adapter.send_notification(stakeholder, anomaly, urgency)
                
                if success:
                    successful_channels.append(channel)
                    
                self.notification_history.append({
                    "stakeholder_id": stakeholder.id,
                    "anomaly_fingerprint": anomaly.fingerprint,
                    "channel": channel,
                    "urgency": urgency,
                    "success": success,
                    "timestamp": datetime.now()
                })
                
        return successful_channels

class RoutingOrchestrator:
    """Orchestrates the routing of anomaly alerts based on policies"""
    
    def __init__(
        self, 
        stakeholder_registry: StakeholderRegistry,
        notification_gateway: NotificationGateway,
        risk_scorer: RiskScorer
    ):
        self.stakeholder_registry = stakeholder_registry
        self.notification_gateway = notification_gateway
        self.risk_scorer = risk_scorer
        self.policies: List[RoutingPolicy] = []
        self.routing_history: List[Dict] = []
        
    def add_policy(self, policy: RoutingPolicy) -> None:
        """Add a routing policy to the orchestrator"""
        self.policies.append(policy)
        
    async def route_anomaly(self, anomaly: Anomaly) -> Dict[str, Any]:
        """Route an anomaly to appropriate stakeholders based on policies"""
        risk_score = self.risk_scorer.calculate_risk_score(anomaly)
        urgency = self.risk_scorer.get_urgency(risk_score)
        
        all_stakeholders = self.stakeholder_registry.get_available_stakeholders()
        targeted_stakeholders = set()
        
        # Apply each routing policy
        for policy in self.policies:
            if policy.should_route(anomaly, risk_score):
                policy_stakeholders = policy.get_stakeholders(
                    anomaly, risk_score, all_stakeholders
                )
                targeted_stakeholders.update(policy_stakeholders)
        
        # Notify all targeted stakeholders
        notification_results = {}
        for stakeholder in targeted_stakeholders:
            channels = await self.notification_gateway.notify_stakeholder(
                stakeholder, anomaly, urgency
            )
            notification_results[stakeholder.id] = channels
            
        # Record routing decision
        routing_record = {
            "anomaly_fingerprint": anomaly.fingerprint,
            "service_name": anomaly.service_name,
            "risk_score": risk_score,
            "urgency": urgency,
            "stakeholders_notified": [s.id for s in targeted_stakeholders],
            "notification_results": notification_results,
            "timestamp": datetime.now()
        }
        self.routing_history.append(routing_record)
        
        return routing_record

# Extension of the AlertRouter class from main.py
class AlertRouter:
    def __init__(self, routing_orchestrator: RoutingOrchestrator):
        self.routing_orchestrator = routing_orchestrator
        
    async def route_anomaly(self, anomaly: Anomaly) -> Dict[str, Any]:
        """Route an anomaly through the orchestrator"""
        return await self.routing_orchestrator.route_anomaly(anomaly)
        
    async def route_anomalies(self, anomalies: List[Anomaly]) -> List[Dict[str, Any]]:
        """Route multiple anomalies"""
        results = []
        for anomaly in anomalies:
            result = await self.route_anomaly(anomaly)
            results.append(result)
        return results