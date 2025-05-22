class AlertEventEnvelope:
    def __init__(self, alert_id, anomaly, timestamp):
        self.alert_id = alert_id
        self.anomaly = anomaly
        self.timestamp = timestamp
        self.metadata = {}
        self.extensions = {}
        
        # New fields for escalation tracking
        self.escalation = EscalationMetadata()
    
    def add_extension(self, name, data):
        """Add structured extension data to the alert event"""
        self.extensions[name] = data
        return self

class EscalationMetadata:
    def __init__(self):
        self.level = 0  # Current escalation level (0 = initial alert)
        self.history = []  # List of previous escalation events
        self.lineage = {}  # Full escalation tree with context
        self.breakthrough_reason = None  # Reason for breaking through acknowledgment
        self.last_escalated_at = None  # Timestamp of last escalation
        
    def escalate(self, level, reason, context=None):
        """Record an escalation event"""
        event = {
            "from_level": self.level,
            "to_level": level,
            "timestamp": datetime.utcnow().isoformat(),
            "reason": reason,
            "context": context or {}
        }
        
        self.level = level
        self.last_escalated_at = event["timestamp"]
        self.history.append(event)
        
        # Update the lineage tree
        if level not in self.lineage:
            self.lineage[level] = []
        self.lineage[level].append(event)
        
        return self
    
    def record_breakthrough(self, reason, frequency_count, ack_details):
        """Record when an alert breaks through an acknowledgment"""
        self.breakthrough_reason = {
            "reason": reason,
            "frequency_count": frequency_count,
            "acknowledgment": ack_details,
            "timestamp": datetime.utcnow().isoformat()
        }
        return self