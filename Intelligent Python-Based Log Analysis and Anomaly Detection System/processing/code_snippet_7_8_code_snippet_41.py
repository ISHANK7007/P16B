class RoutingTraceCollector:
    """Collects and stores detailed routing traces for analysis"""
    
    def __init__(self):
        self.traces = {}
        self.active_collection = None
        self.trace_options = {}
    
    def start_collection(self, collection_name, trace_options=None):
        """Start a new trace collection"""
        self.active_collection = collection_name
        self.trace_options = trace_options or {
            "capture_rule_evaluations": True,
            "capture_team_notifications": True,
            "capture_escalations": True,
            "capture_timing": True
        }
        
    def start_trace(self, entity_id):
        """Start a new trace for an entity"""
        trace_id = str(uuid.uuid4())
        
        trace = {
            "id": trace_id,
            "entity_id": entity_id,
            "collection": self.active_collection,
            "start_time": datetime.utcnow().isoformat(),
            "events": [],
            "summary": {
                "rules_evaluated": 0,
                "rules_matched": 0,
                "teams_notified": set(),
                "escalation_count": 0,
                "terminal_state": None
            }
        }
        
        self.traces[trace_id] = trace
        return trace_id
    
    def record_rule_evaluation(self, trace_id, rule_id, matched, duration_ms=None):
        """Record a rule evaluation event"""
        if not self.trace_options.get("capture_rule_evaluations", True):
            return
            
        trace = self.traces.get(trace_id)
        if not trace:
            return
            
        event = {
            "type": "rule_evaluation",
            "timestamp": datetime.utcnow().isoformat(),
            "rule_id": rule_id,
            "matched": matched
        }
        
        if duration_ms is not None and self.trace_options.get("capture_timing", True):
            event["duration_ms"] = duration_ms
            
        trace["events"].append(event)
        
        # Update summary
        trace["summary"]["rules_evaluated"] += 1
        if matched:
            trace["summary"]["rules_matched"] += 1
    
    def record_team_notification(self, trace_id, team_id, channel, priority):
        """Record a team notification event"""
        if not self.trace_options.get("capture_team_notifications", True):
            return
            
        trace = self.traces.get(trace_id)
        if not trace:
            return
            
        event = {
            "type": "team_notification",
            "timestamp": datetime.utcnow().isoformat(),
            "team_id": team_id,
            "channel": channel,
            "priority": priority
        }
        
        trace["events"].append(event)
        
        # Update summary
        trace["summary"]["teams_notified"].add(team_id)
    
    def record_escalation(self, alert_id, escalation_result):
        """Record an escalation event"""
        if not self.trace_options.get("capture_escalations", True):
            return
            
        # Find trace by alert ID
        trace = None
        for t in self.traces.values():
            if t["entity_id"] == alert_id:
                trace = t
                break
                
        if not trace:
            return
            
        event = {
            "type": "escalation",
            "timestamp": datetime.utcnow().isoformat(),
            "from_level": escalation_result["from_level"],
            "to_level": escalation_result["to_level"],
            "reason": escalation_result["reason"]
        }
        
        trace["events"].append(event)
        
        # Update summary
        trace["summary"]["escalation_count"] += 1
    
    def record_team_action(self, alert_id, team_id, action):
        """Record a team action event"""
        # Find trace by alert ID
        trace = None
        for t in self.traces.values():
            if t["entity_id"] == alert_id:
                trace = t
                break
                
        if not trace:
            return
            
        event = {
            "type": "team_action",
            "timestamp": datetime.utcnow().isoformat(),
            "team_id": team_id,
            "action": action
        }
        
        trace["events"].append(event)
    
    def complete_trace(self, trace_id, terminal_state):
        """Mark a trace as complete with terminal state"""
        trace = self.traces.get(trace_id)
        if not trace:
            return
            
        trace["end_time"] = datetime.utcnow().isoformat()
        trace["summary"]["terminal_state"] = terminal_state
        
        # Convert team set to list for serialization
        trace["summary"]["teams_notified"] = list(trace["summary"]["teams_notified"])
    
    async def get_trace(self, trace_id):
        """Get a complete trace by ID"""
        return self.traces.get(trace_id)