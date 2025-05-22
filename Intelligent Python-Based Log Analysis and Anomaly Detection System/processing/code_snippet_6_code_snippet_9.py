class TracedRoutingOrchestrator(EnhancedRoutingOrchestrator):
    """Routing orchestrator with integrated trace capabilities"""
    
    def __init__(
        self,
        stakeholder_registry: StakeholderRegistry,
        notification_gateway: NotificationGateway,
        risk_scorer: RiskScorer,
        alert_tracker: AlertTracker,
        escalation_engine: EscalationPolicyEngine,
        trace_manager: RoutingTraceManager
    ):
        super().__init__(
            stakeholder_registry, 
            notification_gateway, 
            risk_scorer, 
            alert_tracker, 
            escalation_engine
        )
        self.trace_manager = trace_manager
        
    async def route_anomaly(self, anomaly: Anomaly) -> Dict[str, Any]:
        """Route an anomaly with detailed tracing"""
        # Create or get trace for this anomaly
        fingerprint = anomaly.fingerprint
        trace = self.trace_manager.get_trace(fingerprint)
        
        if not trace:
            trace = self.trace_manager.create_trace(fingerprint, anomaly)
        
        # Record initial routing decision
        self.trace_manager.add_decision(
            fingerprint,
            DecisionType.ROUTING,
            "RoutingOrchestrator",
            input_state={"anomaly_type": anomaly.anomaly_type.name,
                        "service": anomaly.service_name,
                        "criticality": anomaly.service_criticality.name,
                        "confidence": anomaly.confidence}
        )
        
        # Check if this is a known fingerprint
        if self.alert_tracker.alerts.get(fingerprint, None):
            # Check if it's suppressed
            if self.alert_tracker.is_suppressed(fingerprint):
                self.trace_manager.add_decision(
                    fingerprint,
                    DecisionType.SUPPRESSION,
                    "AlertTracker",
                    notes="Alert is currently suppressed",
                    output_state={"status": "suppressed"}
                )
                return {"status": "suppressed", "fingerprint": fingerprint, 
                        "trace_id": trace.trace_id}
            
            # This is a repeat alert - might need escalation
            existing_alert = self.alert_tracker.alerts[fingerprint]
            
            # Record repeat detection
            self.trace_manager.add_decision(
                fingerprint,
                DecisionType.ANOMALY_CLASSIFICATION,
                "AlertTracker",
                notes="Repeat alert detected",
                input_state={"alert_count": existing_alert["count"]},
                output_state={"is_repeat": True}
            )
            
            # If this alert is already at a higher escalation level, maintain that
            if existing_alert["current_escalation_level"] != EscalationLevel.INITIAL:
                # Get applicable escalation rule
                rules = self.escalation_engine.get_applicable_rules(
                    anomaly, 
                    existing_alert["current_escalation_level"]
                )
                
                if rules:
                    # Record escalation rule selection
                    self.trace_manager.add_decision(
                        fingerprint,
                        DecisionType.ESCALATION,
                        "EscalationPolicyEngine",
                        rule_id=rules[0].id,
                        rule_name=rules[0].name,
                        notes="Maintaining current escalation level",
                        output_state={"level": existing_alert["current_escalation_level"].name}
                    )
                    
                    # Re-notify based on the current escalation rule
                    escalation_result = await self.escalation_engine._perform_escalation(
                        fingerprint, anomaly, rules[0]
                    )
                    
                    self.trace_manager.add_decision(
                        fingerprint,
                        DecisionType.ROUTING,
                        "EscalationPolicyEngine",
                        rule_id=rules[0].id,
                        output_state={"stakeholders": escalation_result["notified_stakeholders"]}
                    )
                    
                    return {
                        "status": "escalated_repeat",
                        "fingerprint": fingerprint,
                        "escalation": escalation_result,
                        "trace_id": trace.trace_id
                    }
        
        # Calculate risk score with tracing
        risk_score = self.risk_scorer.calculate_risk_score(anomaly)
        urgency = self.risk_scorer.get_urgency(risk_score)
        
        self.trace_manager.add_decision(
            fingerprint,
            DecisionType.ANOMALY_CLASSIFICATION,
            "RiskScorer",
            output_state={"risk_score": risk_score, "urgency": urgency.name}
        )
        
        # Get available stakeholders
        all_stakeholders = self.stakeholder_registry.get_available_stakeholders()
        targeted_stakeholders = set()
        
        # Apply each routing policy with tracing
        for i, policy in enumerate(self.policies):
            self.trace_manager.add_decision(
                fingerprint,
                DecisionType.POLICY_EVALUATION,
                f"RoutingPolicy[{i}]",
                rule_id=getattr(policy, 'id', f'policy-{i}'),
                rule_name=policy.__class__.__name__,
                input_state={"policy_type": policy.__class__.__name__}
            )
            
            if policy.should_route(anomaly, risk_score):
                policy_stakeholders = policy.get_stakeholders(
                    anomaly, risk_score, all_stakeholders
                )
                
                self.trace_manager.add_decision(
                    fingerprint,
                    DecisionType.STAKEHOLDER_SELECTION,
                    f"RoutingPolicy[{i}]",
                    rule_id=getattr(policy, 'id', f'policy-{i}'),
                    output_state={
                        "stakeholder_count": len(policy_stakeholders),
                        "stakeholders": [s.id for s in policy_stakeholders]
                    }
                )
                
                targeted_stakeholders.update(policy_stakeholders)
        
        # Notify all targeted stakeholders with tracing
        notification_results = {}
        for stakeholder in targeted_stakeholders:
            self.trace_manager.add_decision(
                fingerprint,
                DecisionType.CHANNEL_SELECTION,
                "NotificationGateway",
                metadata={"stakeholder_id": stakeholder.id, "urgency": urgency.name}
            )
            
            channels = await self.notification_gateway.notify_stakeholder(
                stakeholder, anomaly, urgency
            )
            
            self.trace_manager.add_decision(
                fingerprint,
                DecisionType.CHANNEL_SELECTION,
                "NotificationGateway",
                metadata={"stakeholder_id": stakeholder.id},
                output_state={"channels": channels, "success": len(channels) > 0}
            )
            
            notification_results[stakeholder.id] = channels
            
        # Record routing decision
        routing_record = {
            "anomaly_fingerprint": fingerprint,
            "service_name": anomaly.service_name,
            "risk_score": risk_score,
            "urgency": urgency,
            "stakeholders_notified": [s.id for s in targeted_stakeholders],
            "notification_results": notification_results,
            "timestamp": datetime.now(),
            "trace_id": trace.trace_id
        }
        self.routing_history.append(routing_record)
        
        # Complete the trace
        trace.current_state = "ROUTED"
        
        # Register with the alert tracker
        self.alert_tracker.register_alert(anomaly, routing_record)
        
        return routing_record