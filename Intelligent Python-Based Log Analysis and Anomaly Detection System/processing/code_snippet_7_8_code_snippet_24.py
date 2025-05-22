class MitigationTracker:
    """Tracks confirmed mitigations for anomalies"""
    
    def __init__(self, store):
        self.store = store
        self.verification_service = MitigationVerificationService()
    
    async def register_mitigation(self, fingerprint, mitigation_data):
        """Register a mitigation for an anomaly fingerprint"""
        record = MitigationRecord(
            fingerprint=fingerprint,
            mitigation_type=mitigation_data["type"],
            description=mitigation_data["description"],
            applied_by=mitigation_data["applied_by"],
            applied_at=datetime.utcnow(),
            verification_status="pending",
            confidence=0.0
        )
        
        await self.store.store_mitigation(record)
        
        # Schedule verification check
        self._schedule_verification(fingerprint, record.id)
        
        return record
    
    async def is_mitigated(self, fingerprint):
        """Check if an anomaly has a confirmed mitigation"""
        record = await self.store.get_latest_mitigation(fingerprint)
        
        if not record:
            return False
            
        return record.verification_status == "confirmed" and record.confidence >= 0.8
    
    async def get_mitigation_evidence(self, fingerprint):
        """Get evidence of mitigation for a fingerprint"""
        record = await self.store.get_latest_mitigation(fingerprint)
        
        if not record or record.verification_status != "confirmed":
            return None
            
        return {
            "mitigation_id": record.id,
            "mitigation_type": record.mitigation_type,
            "applied_at": record.applied_at.isoformat(),
            "verification_status": record.verification_status,
            "confidence": record.confidence,
            "verification_metrics": record.verification_metrics
        }
    
    async def _schedule_verification(self, fingerprint, mitigation_id):
        """Schedule verification checks for a mitigation"""
        # Schedule immediate verification
        asyncio.create_task(self._verify_mitigation(fingerprint, mitigation_id))
        
        # Schedule follow-up verifications at intervals
        for delay in [5*60, 15*60, 60*60]:  # 5m, 15m, 1h
            asyncio.create_task(self._delayed_verification(fingerprint, mitigation_id, delay))
    
    async def _delayed_verification(self, fingerprint, mitigation_id, delay):
        await asyncio.sleep(delay)
        await self._verify_mitigation(fingerprint, mitigation_id)
    
    async def _verify_mitigation(self, fingerprint, mitigation_id):
        """Verify if a mitigation is effective"""
        record = await self.store.get_mitigation(mitigation_id)
        
        if not record:
            return False
            
        # Get verification metrics for this mitigation
        verification_result = await self.verification_service.verify_mitigation(
            fingerprint, 
            record.mitigation_type
        )
        
        # Update mitigation record
        record.verification_status = verification_result.status
        record.confidence = verification_result.confidence
        record.verification_metrics = verification_result.metrics
        record.last_verified_at = datetime.utcnow()
        
        await self.store.update_mitigation(record)
        
        # If confirmed with high confidence, trigger de-escalations
        if record.verification_status == "confirmed" and record.confidence >= 0.8:
            await self._trigger_de_escalations(fingerprint, record)
            
        return record.verification_status == "confirmed"