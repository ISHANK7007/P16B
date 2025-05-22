class EnhancedAlertRouter:
    # ... (other methods from previous response)
    
    async def _process_alert_batch(self, alerts):
        results = []
        for alert in alerts:
            # Create or retrieve the envelope
            envelope = self._get_or_create_envelope(alert)
            
            # Check for existing acknowledgments
            ack_status = self.fingerprint_registry.get_acknowledgment(alert.anomaly.fingerprint)
            
            if ack_status and ack_status.is_valid():
                # Check breakthrough conditions
                recent_occurrences = await self.anomaly_store.count_occurrences(
                    fingerprint=alert.anomaly.fingerprint,
                    time_window=self.config.breakthrough_window
                )
                
                if recent_occurrences > ack_status.breakthrough_threshold:
                    # Record escalation with breakthrough metadata
                    envelope.escalation.record_breakthrough(
                        reason="frequency_threshold_exceeded",
                        frequency_count=recent_occurrences,
                        ack_details=ack_status.to_dict()
                    )
                    envelope.escalation.escalate(
                        level=self._calculate_escalation_level(alert, ack_status),
                        reason="acknowledgment_breakthrough",
                        context={
                            "occurrences": recent_occurrences,
                            "threshold": ack_status.breakthrough_threshold,
                            "window": self.config.breakthrough_window
                        }
                    )
                    results.append(self._route_escalated_alert(envelope))
                else:
                    # Log suppressed alert but don't escalate
                    results.append(None)
            else:
                # Normal alert flow
                results.append(self._route_initial_alert(envelope))
        
        return [r for r in results if r is not None]
    
    def _calculate_escalation_level(self, alert, ack_status):
        """Calculate the appropriate escalation level based on alert properties and history"""
        base_level = 1  # Start at level 1 for initial escalation
        
        # Add level based on alert criticality
        criticality_boost = {
            ServiceCriticality.CRITICAL: 2,
            ServiceCriticality.HIGH: 1,
            ServiceCriticality.MEDIUM: 0,
            ServiceCriticality.LOW: 0
        }.get(alert.anomaly.criticality, 0)
        
        # Add level based on frequency
        frequency_boost = min(3, ack_status.breach_count // 5)
        
        return base_level + criticality_boost + frequency_boost
    
    def _route_escalated_alert(self, envelope):
        """Route an alert that has been escalated with appropriate metadata"""
        # Add standardized escalation extension data
        envelope.add_extension("escalation_data", {
            "level": envelope.escalation.level,
            "history_count": len(envelope.escalation.history),
            "last_escalated_at": envelope.escalation.last_escalated_at,
            "breakthrough_reason": envelope.escalation.breakthrough_reason,
            "is_repeated": len(envelope.escalation.history) > 0
        })
        
        # Route based on escalation level
        routing_targets = self.escalation_router.get_targets_for_level(
            envelope.escalation.level,
            envelope.anomaly.service_name,
            envelope.anomaly.criticality
        )
        
        return self.notification_service.send_to_targets(envelope, routing_targets)