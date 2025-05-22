class DeEscalationEngine:
    def __init__(self, policy_registry, alert_store, fingerprint_registry):
        self.policy_registry = policy_registry
        self.alert_store = alert_store
        self.fingerprint_registry = fingerprint_registry
        self.resolution_validator = ResolutionValidator()
        self.mitigation_tracker = MitigationTracker()
    
    async def evaluate_de_escalation(self, alert_envelope, trigger_type, evidence=None):
        """Evaluate if an alert should be de-escalated based on trigger and evidence"""
        correlation_id = alert_envelope.extensions.get("correlation_id")
        
        # Build de-escalation context
        context = DeEscalationContext(
            alert=alert_envelope,
            trigger_type=trigger_type,
            evidence=evidence or {},
            current_escalation_level=alert_envelope.escalation.level,
            fingerprint=alert_envelope.anomaly.fingerprint
        )
        
        # Check if mitigation is confirmed
        is_mitigated = await self.mitigation_tracker.is_mitigated(
            alert_envelope.anomaly.fingerprint
        )
        if is_mitigated:
            context.add_evidence("confirmed_mitigation", 
                await self.mitigation_tracker.get_mitigation_evidence(
                    alert_envelope.anomaly.fingerprint
                )
            )

        # Load applicable de-escalation policies
        policies = self._load_applicable_policies(alert_envelope)
        
        # Evaluate policies to determine de-escalation action
        action = await self._evaluate_policies(policies, context)
        
        if action and action.should_apply:
            # Apply the de-escalation action
            await self._apply_de_escalation(alert_envelope, action, context)
            
            # For multi-team alerts, coordinate de-escalation
            if correlation_id:
                await self._coordinate_multi_team_de_escalation(correlation_id, action, context)
            
            # Record de-escalation event
            await self._record_de_escalation(alert_envelope, action, context)
            
            return action
        
        return None
    
    async def _evaluate_policies(self, policies, context):
        """Evaluate de-escalation policies to determine appropriate action"""
        # Sort policies by priority (specific to general)
        sorted_policies = sorted(policies, key=lambda p: p.specificity, reverse=True)
        
        for policy in sorted_policies:
            # Check if policy conditions match
            if await policy.matches(context):
                # Policy matched, create de-escalation action
                return DeEscalationAction(
                    policy_id=policy.id,
                    target_level=policy.calculate_target_level(context),
                    reason=policy.get_reason(),
                    evidence_requirements=policy.get_evidence_requirements(),
                    should_apply=await self._validate_evidence(
                        context, policy.get_evidence_requirements()
                    )
                )
        
        return None
    
    async def _validate_evidence(self, context, requirements):
        """Validate if the evidence meets policy requirements"""
        if not requirements:
            return True
            
        # Check each evidence requirement
        for req_type, req_level in requirements.items():
            evidence = context.get_evidence(req_type)
            
            if not evidence:
                return False
                
            # Validate evidence meets confidence threshold
            if not self.resolution_validator.validate_evidence(
                evidence, req_type, req_level
            ):
                return False
                
        return True
    
    async def _apply_de_escalation(self, alert_envelope, action, context):
        """Apply de-escalation action to alert"""
        # Record original level for audit
        original_level = alert_envelope.escalation.level
        
        # Update alert escalation level
        alert_envelope.escalation.level = action.target_level
        
        # Add de-escalation metadata
        alert_envelope.add_extension("de_escalation", {
            "original_level": original_level,
            "new_level": action.target_level,
            "policy_id": action.policy_id,
            "reason": action.reason,
            "timestamp": datetime.utcnow().isoformat(),
            "evidence_types": list(context.evidence.keys())
        })
        
        # If fully de-escalated, update status
        if action.target_level == 0:
            alert_envelope.status = "resolved"
            
            # Register resolution with fingerprint registry for future reference
            await self.fingerprint_registry.register_resolution(
                alert_envelope.anomaly.fingerprint,
                ResolutionRecord(
                    fingerprint=alert_envelope.anomaly.fingerprint,
                    resolution_type="de_escalated",
                    evidence=context.evidence,
                    timestamp=datetime.utcnow()
                )
            )
        
        # Update alert in store
        await self.alert_store.update_alert(alert_envelope)
        
        return True