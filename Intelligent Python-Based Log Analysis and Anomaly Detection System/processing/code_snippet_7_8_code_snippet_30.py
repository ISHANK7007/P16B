class EventType(Enum):
    """Types of events recorded in the escalation ledger"""
    ALERT_CREATED = "alert_created"
    RULE_EVALUATION = "rule_evaluation"
    ESCALATION = "escalation"
    DE_ESCALATION = "de_escalation"
    ACKNOWLEDGMENT = "acknowledgment"
    TEAM_NOTIFICATION = "team_notification"
    TEAM_COMMENT = "team_comment"
    TEAM_ACTION = "team_action"
    ROUTING_DECISION = "routing_decision"
    COORDINATION = "coordination"
    MITIGATION = "mitigation"
    VERIFICATION = "verification"
    STATUS_CHANGE = "status_change"
    SYSTEM_RECOVERY = "system_recovery"

class EscalationEvent:
    """Immutable record of an escalation event"""
    
    def __init__(self, alert_id, event_type, sequence_id, timestamp, data, 
                 actor, metadata, previous_hash=None, hash=None):
        self.alert_id = alert_id
        self.event_type = event_type
        self.sequence_id = sequence_id
        self.timestamp = timestamp
        self.data = data  # Event-specific data payload
        self.actor = actor  # User or system component that triggered event
        self.metadata = metadata  # Additional context
        self.previous_hash = previous_hash  # Hash of previous event (chain)
        self.hash = hash  # Integrity hash of this event
        
    def to_dict(self):
        """Convert to dictionary for serialization"""
        return {
            "alert_id": self.alert_id,
            "event_type": self.event_type,
            "sequence_id": self.sequence_id,
            "timestamp": self.timestamp,
            "data": self.data,
            "actor": self.actor,
            "metadata": self.metadata,
            "previous_hash": self.previous_hash,
            "hash": self.hash
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create event from dictionary"""
        return cls(
            alert_id=data["alert_id"],
            event_type=data["event_type"],
            sequence_id=data["sequence_id"],
            timestamp=data["timestamp"],
            data=data["data"],
            actor=data["actor"],
            metadata=data["metadata"],
            previous_hash=data["previous_hash"],
            hash=data["hash"]
        )