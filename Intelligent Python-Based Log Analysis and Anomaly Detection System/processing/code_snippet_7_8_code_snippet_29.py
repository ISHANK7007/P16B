class EscalationLedger:
    """Immutable, versioned ledger of all escalation events with audit capabilities"""
    
    def __init__(self, storage_engine, integrity_verifier):
        self.storage = storage_engine  # Persistent storage backend
        self.verifier = integrity_verifier  # Cryptographic integrity verification
        self.sequence_tracker = SequenceTracker()  # Ensures serial consistency
        self.backup_coordinator = BackupCoordinator()  # Manages replication
    
    async def record_event(self, alert_id, event_type, data, actor=None, metadata=None):
        """Record an immutable escalation event in the ledger"""
        # Create versioned event record
        sequence_id = await self.sequence_tracker.next_sequence(alert_id)
        
        event = EscalationEvent(
            alert_id=alert_id,
            event_type=event_type,
            sequence_id=sequence_id,
            timestamp=datetime.utcnow().isoformat(),
            data=data,
            actor=actor or "system",
            metadata=metadata or {},
            previous_hash=await self._get_latest_event_hash(alert_id)
        )
        
        # Generate integrity hash (includes previous_hash for chaining)
        event.hash = self.verifier.generate_hash(event)
        
        # Persist with durability guarantees
        await self.storage.store_event(event, durability_level=DurabilityLevel.COMMITTED)
        
        # Update sequence tracker for consistency
        await self.sequence_tracker.mark_persisted(alert_id, sequence_id)
        
        # Trigger async backup if configured
        self.backup_coordinator.schedule_backup(event)
        
        return event
    
    async def get_alert_history(self, alert_id, include_data=True, filter_types=None):
        """Retrieve complete history for an alert with optional filtering"""
        events = await self.storage.get_events(
            alert_id=alert_id, 
            include_data=include_data,
            filter_types=filter_types
        )
        
        # Verify chain integrity
        if not await self._verify_event_chain(events):
            raise LedgerIntegrityError(f"Integrity violation in event chain for alert {alert_id}")
            
        return events
    
    async def rehydrate_alert_state(self, alert_id, target_sequence=None):
        """Rehydrate an alert to its complete state at a specific sequence point"""
        # Get all events up to target sequence
        events = await self.storage.get_events(
            alert_id=alert_id,
            max_sequence=target_sequence
        )
        
        # Verify chain integrity
        if not await self._verify_event_chain(events):
            raise LedgerIntegrityError(f"Integrity violation during rehydration for alert {alert_id}")
        
        # Reconstruct alert state by replaying events
        alert_state = AlertState(alert_id)
        for event in events:
            alert_state.apply_event(event)
            
        return alert_state
    
    async def get_cross_team_interactions(self, correlation_id):
        """Get all cross-team interactions for a correlated alert group"""
        # Query across all related alert IDs
        alert_ids = await self.storage.get_correlated_alerts(correlation_id)
        
        interactions = []
        for alert_id in alert_ids:
            team_events = await self.storage.get_events(
                alert_id=alert_id,
                filter_types=[
                    EventType.TEAM_NOTIFICATION,
                    EventType.TEAM_COMMENT,
                    EventType.TEAM_ACTION,
                    EventType.COORDINATION
                ]
            )
            interactions.extend(team_events)
            
        # Sort by timestamp for unified timeline
        interactions.sort(key=lambda e: e.timestamp)
        return interactions
    
    async def _get_latest_event_hash(self, alert_id):
        """Get hash of the latest event for an alert"""
        latest = await self.storage.get_latest_event(alert_id)
        return latest.hash if latest else None
        
    async def _verify_event_chain(self, events):
        """Verify the integrity of the event chain"""
        if not events:
            return True
            
        prev_hash = None
        for event in events:
            # Verify this event's hash
            if not self.verifier.verify_hash(event):
                return False
                
            # Verify chain linkage
            if prev_hash and event.previous_hash != prev_hash:
                return False
                
            prev_hash = event.hash
            
        return True