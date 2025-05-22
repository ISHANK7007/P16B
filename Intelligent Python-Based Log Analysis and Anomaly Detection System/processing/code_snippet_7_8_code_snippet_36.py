class LedgerAuditService:
    """Service for generating compliance-ready audit reports from the ledger"""
    
    def __init__(self, escalation_ledger):
        self.ledger = escalation_ledger
        
    async def generate_audit_report(self, alert_id, format="json"):
        """Generate a comprehensive audit report for an alert"""
        # Retrieve complete alert history
        events = await self.ledger.get_alert_history(alert_id)
        
        # Build comprehensive timeline
        timeline = []
        escalation_map = {}
        rule_evaluations = []
        team_interactions = []
        
        for event in events:
            # Add to timeline
            timeline.append({
                "timestamp": event.timestamp,
                "type": event.event_type,
                "actor": event.actor,
                "sequence": event.sequence_id
            })
            
            # Track specific event types
            if event.event_type == EventType.ESCALATION:
                escalation_map[event.data["level"]] = {
                    "timestamp": event.timestamp,
                    "actor": event.actor,
                    "reason": event.data.get("reason")
                }
            elif event.event_type == EventType.RULE_EVALUATION:
                rule_evaluations.append({
                    "timestamp": event.timestamp,
                    "matched_rules": event.data.get("matched_rules", 0),
                    "total_rules": event.data.get("evaluated_rules", 0)
                })
            elif event.event_type in [
                EventType.TEAM_NOTIFICATION,
                EventType.TEAM_COMMENT,
                EventType.TEAM_ACTION
            ]:
                team_interactions.append({
                    "timestamp": event.timestamp,
                    "type": event.event_type,
                    "team_id": event.data.get("team_id"),
                    "actor": event.actor,
                    "details": event.data
                })
        
        # Build report
        report = {
            "alert_id": alert_id,
            "report_id": str(uuid.uuid4()),
            "generated_at": datetime.utcnow().isoformat(),
            "event_count": len(events),
            "timeline": timeline,
            "escalation_history": escalation_map,
            "rule_evaluations_summary": {
                "count": len(rule_evaluations),
                "details": rule_evaluations
            },
            "team_interactions": {
                "count": len(team_interactions),
                "details": team_interactions
            },
            "hash_verification": await self._verify_report_integrity(events)
        }
        
        # Format appropriately
        if format == "pdf":
            return await self._generate_pdf_report(report)
        elif format == "csv":
            return await self._generate_csv_report(report)
        else:
            return report