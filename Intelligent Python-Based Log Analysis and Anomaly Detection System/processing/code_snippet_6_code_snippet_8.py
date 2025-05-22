from typing import Tuple, Optional
from datetime import datetime

class Anomaly:
    def __init__(self, id='anomaly-001', message='Test anomaly'):
        self.id = id
        self.message = message

    def __repr__(self):
        return f"<Anomaly id={self.id} message={self.message}>"

from dataclasses import dataclass, field
from enum import Enum, auto
from datetime import datetime
from typing import Dict, List, Any, Optional, Union, Set
import json
import uuid

class DecisionType(Enum):
    POLICY_EVALUATION = auto()
    ESCALATION = auto()
    SUPPRESSION = auto()
    OVERRIDE = auto()
    ROUTING = auto()
    STAKEHOLDER_SELECTION = auto()
    CHANNEL_SELECTION = auto()
    INCIDENT_CREATION = auto()
    FINGERPRINT_CLASSIFICATION = auto()
    ANOMALY_CLASSIFICATION = auto()

@dataclass
class DecisionPoint:
    """Represents a single decision in the routing process"""
    timestamp: datetime
    decision_type: DecisionType
    component: str  # Which component made the decision
    rule_id: Optional[str] = None  # If applicable
    rule_name: Optional[str] = None  # Human-readable name
    input_state: Dict[str, Any] = field(default_factory=dict)  # State before decision
    output_state: Dict[str, Any] = field(default_factory=dict)  # State after decision
    notes: Optional[str] = None  # Any additional context
    metadata: Dict[str, Any] = field(default_factory=dict)  # Additional metadata
    success: bool = True  # Whether the decision point succeeded
    error: Optional[str] = None  # Error message if any
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "decision_type": self.decision_type.name,
            "component": self.component,
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "input_state": self.input_state,
            "output_state": self.output_state,
            "notes": self.notes,
            "metadata": self.metadata,
            "success": self.success,
            "error": self.error
        }

class RoutingTrace:
    """Complete trace of an alert's routing journey"""
    
    def __init__(self, alert_fingerprint: str, initial_anomaly: Anomaly):
        self.trace_id = str(uuid.uuid4())
        self.alert_fingerprint = alert_fingerprint
        self.start_time = datetime.now()
        self.last_update = self.start_time
        self.decision_points: List[DecisionPoint] = []
        self.manual_overrides: List[DecisionPoint] = []
        self.escalation_history: List[DecisionPoint] = []
        self.stakeholders_notified: Set[str] = set()
        self.channels_used: Dict[str, List[str]] = {}  # stakeholder -> channels
        self.current_state = "INITIAL"
        
        # Initial anomaly metadata
        self.service = initial_anomaly.service_name
        self.service_criticality = initial_anomaly.service_criticality
        self.anomaly_type = initial_anomaly.anomaly_type
        self.confidence = initial_anomaly.confidence
        
        # Flag if this is a debug trace (more verbose)
        self.debug_mode = False
    
    def add_decision(self, decision: DecisionPoint) -> None:
        """Add a decision point to the trace"""
        self.decision_points.append(decision)
        self.last_update = datetime.now()
        
        # Also add to specialized lists based on decision type
        if decision.decision_type == DecisionType.OVERRIDE:
            self.manual_overrides.append(decision)
        elif decision.decision_type == DecisionType.ESCALATION:
            self.escalation_history.append(decision)
            
        # Track stakeholders and channels
        if decision.decision_type == DecisionType.ROUTING:
            if 'stakeholders' in decision.output_state:
                for stakeholder in decision.output_state['stakeholders']:
                    self.stakeholders_notified.add(stakeholder)
                    
        if decision.decision_type == DecisionType.CHANNEL_SELECTION:
            stakeholder = decision.metadata.get('stakeholder_id')
            channels = decision.output_state.get('channels', [])
            if stakeholder and channels:
                if stakeholder not in self.channels_used:
                    self.channels_used[stakeholder] = []
                self.channels_used[stakeholder].extend(channels)
    
    def enable_debug(self, enabled: bool = True) -> None:
        """Enable or disable debug mode for more verbose tracing"""
        self.debug_mode = enabled
        
    def get_timeline(self) -> List[Dict]:
        """Get chronological timeline of all decisions"""
        all_decisions = sorted(self.decision_points, key=lambda d: d.timestamp)
        return [d.to_dict() for d in all_decisions]
    
    def get_failed_decisions(self) -> List[Dict]:
        """Get all decision points that failed"""
        return [d.to_dict() for d in self.decision_points if not d.success]
    
    def to_dict(self) -> Dict:
        """Convert trace to dictionary for serialization"""
        return {
            "trace_id": self.trace_id,
            "alert_fingerprint": self.alert_fingerprint,
            "service": self.service,
            "service_criticality": self.service_criticality.name,
            "anomaly_type": self.anomaly_type.name,
            "confidence": self.confidence,
            "start_time": self.start_time.isoformat(),
            "last_update": self.last_update.isoformat(),
            "current_state": self.current_state,
            "stakeholders_notified": list(self.stakeholders_notified),
            "channels_used": self.channels_used,
            "decision_count": len(self.decision_points),
            "override_count": len(self.manual_overrides),
            "escalation_count": len(self.escalation_history)
        }
        
    def to_json(self, include_decisions: bool = False) -> str:
        """Convert trace to JSON string"""
        data = self.to_dict()
        if include_decisions:
            data["decisions"] = [d.to_dict() for d in self.decision_points]
        return json.dumps(data)

class RoutingTraceManager:
    """Manages collection, storage and retrieval of routing traces"""
    
    def __init__(self, max_traces_in_memory: int = 1000):
        self.traces: Dict[str, RoutingTrace] = {}  # fingerprint -> trace
        self.trace_by_id: Dict[str, RoutingTrace] = {}  # trace_id -> trace
        self.max_traces = max_traces_in_memory
        self.debug_fingerprints: Set[str] = set()  # Fingerprints to debug
    
    def create_trace(self, alert_fingerprint: str, anomaly: Anomaly) -> RoutingTrace:
        """Create a new trace for an alert"""
        trace = RoutingTrace(alert_fingerprint, anomaly)
        
        # If this is a fingerprint we're debugging, enable debug mode
        if alert_fingerprint in self.debug_fingerprints:
            trace.enable_debug()
        
        # Store the trace
        self.traces[alert_fingerprint] = trace
        self.trace_by_id[trace.trace_id] = trace
        
        # Prune old traces if we exceed the limit
        self._prune_traces()
        
        return trace
    
    def add_decision(
        self, 
        alert_fingerprint: str, 
        decision_type: DecisionType,
        component: str,
        rule_id: Optional[str] = None,
        rule_name: Optional[str] = None,
        input_state: Optional[Dict] = None,
        output_state: Optional[Dict] = None,
        notes: Optional[str] = None,
        metadata: Optional[Dict] = None,
        success: bool = True,
        error: Optional[str] = None
    ) -> None:
        """Add a decision point to a trace"""
        if alert_fingerprint not in self.traces:
            return
            
        trace = self.traces[alert_fingerprint]
        decision = DecisionPoint(
            timestamp=datetime.now(),
            decision_type=decision_type,
            component=component,
            rule_id=rule_id,
            rule_name=rule_name,
            input_state=input_state or {},
            output_state=output_state or {},
            notes=notes,
            metadata=metadata or {},
            success=success,
            error=error
        )
        trace.add_decision(decision)
    
    def get_trace(self, alert_fingerprint: str) -> Optional[RoutingTrace]:
        """Get a trace by alert fingerprint"""
        return self.traces.get(alert_fingerprint)
        
    def get_trace_by_id(self, trace_id: str) -> Optional[RoutingTrace]:
        """Get a trace by its ID"""
        return self.trace_by_id.get(trace_id)
    
    def enable_debug_for_fingerprint(self, fingerprint: str) -> None:
        """Enable detailed tracing for a specific fingerprint"""
        self.debug_fingerprints.add(fingerprint)
        if fingerprint in self.traces:
            self.traces[fingerprint].enable_debug()
    
    def export_trace(self, trace_id: str, include_decisions: bool = True) -> Optional[str]:
        """Export a trace to JSON"""
        trace = self.get_trace_by_id(trace_id)
        if not trace:
            return None
        return trace.to_json(include_decisions)
        
    def _prune_traces(self) -> None:
        """Remove oldest traces if we exceed the maximum"""
        if len(self.traces) <= self.max_traces:
            return
            
        # Sort traces by last_update time
        sorted_traces = sorted(self.traces.values(), key=lambda t: t.last_update)
        
        # Remove oldest traces until we're under the limit
        traces_to_remove = len(self.traces) - self.max_traces
        for i in range(traces_to_remove):
            trace = sorted_traces[i]
            del self.traces[trace.alert_fingerprint]
            del self.trace_by_id[trace.trace_id]
            
    def query_traces(
        self,
        service: Optional[str] = None,
        stakeholder: Optional[str] = None,
        min_confidence: Optional[float] = None,
        decision_type: Optional[DecisionType] = None,
        has_error: Optional[bool] = None,
        has_override: Optional[bool] = None,
        time_range: Optional[Tuple[datetime, datetime]] = None
    ) -> List[RoutingTrace]:
        """Query traces based on various criteria"""
        results = []
        
        for trace in self.traces.values():
            # Apply filters
            if service and trace.service != service:
                continue
                
            if stakeholder and stakeholder not in trace.stakeholders_notified:
                continue
                
            if min_confidence is not None and trace.confidence < min_confidence:
                continue
                
            if decision_type:
                decision_types = [d.decision_type for d in trace.decision_points]
                if decision_type not in decision_types:
                    continue
            
            if has_error is not None:
                has_error_decision = any(not d.success for d in trace.decision_points)
                if has_error != has_error_decision:
                    continue
            
            if has_override is not None:
                has_override_decision = len(trace.manual_overrides) > 0
                if has_override != has_override_decision:
                    continue
            
            if time_range:
                start, end = time_range
                if not (start <= trace.start_time <= end):
                    continue
            
            results.append(trace)
            
        return results