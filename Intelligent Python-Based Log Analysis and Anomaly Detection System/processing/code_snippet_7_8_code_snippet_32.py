class AlertRecoveryService:
    """Service for recovering alert state during failover or reconciliation"""
    
    def __init__(self, escalation_ledger, alert_store):
        self.ledger = escalation_ledger
        self.alert_store = alert_store
        self.recovery_tracker = RecoveryTracker()
        
    async def recover_alert(self, alert_id):
        """Recover complete alert state from ledger"""
        # Log recovery attempt
        recovery_id = uuid.uuid4()
        self.recovery_tracker.start_recovery(recovery_id, alert_id)
        
        try:
            # Rehydrate alert state from ledger events
            alert_state = await self.ledger.rehydrate_alert_state(alert_id)
            
            # Convert to AlertEventEnvelope
            envelope = self._state_to_envelope(alert_state)
            
            # Store recovered alert
            await self.alert_store.update_alert(envelope)
            
            # Record recovery event in ledger
            await self.ledger.record_event(
                alert_id=alert_id,
                event_type=EventType.SYSTEM_RECOVERY,
                data={
                    "recovery_id": str(recovery_id),
                    "recovered_sequence": alert_state.latest_sequence,
                    "alert_status": alert_state.status
                },
                metadata={
                    "recovery_timestamp": datetime.utcnow().isoformat()
                }
            )
            
            # Mark recovery as successful
            self.recovery_tracker.complete_recovery(recovery_id)
            
            return envelope
        except Exception as e:
            # Mark recovery as failed
            self.recovery_tracker.fail_recovery(recovery_id, str(e))
            raise AlertRecoveryError(f"Failed to recover alert {alert_id}: {str(e)}")
    
    async def recover_correlated_alerts(self, correlation_id):
        """Recover all alerts in a correlation group"""
        # Get all alert IDs in this correlation group
        alert_ids = await self.alert_store.get_correlated_alert_ids(correlation_id)
        
        # Recover each alert
        results = {}
        for alert_id in alert_ids:
            try:
                envelope = await self.recover_alert(alert_id)
                results[alert_id] = {
                    "status": "recovered",
                    "envelope": envelope
                }
            except Exception as e:
                results[alert_id] = {
                    "status": "failed",
                    "error": str(e)
                }
                
        return results
    
    async def validate_system_state(self):
        """Validate global system state consistency"""
        # Find potentially inconsistent alerts
        inconsistent = await self._find_inconsistent_alerts()
        
        # Auto-recover what we can
        recovered = 0
        failed = 0
        for alert_id in inconsistent:
            try:
                await self.recover_alert(alert_id)
                recovered += 1
            except Exception:
                failed += 1
                
        return {
            "inconsistent_count": len(inconsistent),
            "recovered_count": recovered,
            "failed_count": failed,
            "recovery_needed": failed > 0
        }