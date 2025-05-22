class AlertDebugger:
    """Interface for debugging misrouted alerts"""
    
    def __init__(
        self,
        trace_manager: RoutingTraceManager,
        correction_manager: CorrectionManager,
        analyzer: RoutingTraceAnalyzer,
        routing_orchestrator: TracedRoutingOrchestrator
    ):
        self.trace_manager = trace_manager
        self.correction_manager = correction_manager
        self.analyzer = analyzer
        self.routing_orchestrator = routing_orchestrator
        
    def debug_alert(self, fingerprint: str) -> Dict:
        """Debug a specific alert"""
        trace = self.trace_manager.get_trace(fingerprint)
        if not trace:
            return {"error": "Trace not found for fingerprint"}
            
        corrections = self.correction_manager.get_corrections(fingerprint=fingerprint)
        
        # Enable debug mode for this fingerprint
        self.trace_manager.enable_debug_for_fingerprint(fingerprint)
        
        # Get timeline of decisions
        timeline = trace.get_timeline()
        
        # Get failed decisions
        failures = trace.get_failed_decisions()
        
        # Find similar traces with different routing outcomes
        similar_traces = self._find_similar_traces(trace)
        
        # Generate explanation
        explanation = self._generate_explanation(trace, failures, corrections)
        
        return {
            "fingerprint": fingerprint,
            "service": trace.service,
            "anomaly_type": trace.anomaly_type.name,
            "confidence": trace.confidence,
            "current_state": trace.current_state,
            "stakeholders_notified": list(trace.stakeholders_notified),
            "decision_count": len(timeline),
            "failures": failures,
            "corrections": [self._format_correction(c) for c in corrections],
            "similar_traces": similar_traces,
            "explanation": explanation
        }
    
    def correct_alert_routing(
        self,
        fingerprint: str,
        correct_stakeholders: List[str],
        reason: str,
        corrected_by: str
    ) -> Dict:
        """Correct the routing of an alert"""
        trace = self.trace_manager.get_trace(fingerprint)
        if not trace:
            return {"error": "Trace not found for fingerprint"}
            
        current_stakeholders = list(trace.stakeholders_notified)
        
        # Create correction record
        correction = AlertCorrection(
            alert_fingerprint=fingerprint,
            corrected_by=corrected_by,
            correction_time=datetime.now(),
            original_trace_id=trace.trace_id,
            reason=reason,
            correction_type="routing",
            from_value=current_stakeholders,
            to_value=correct_stakeholders,
            notes=f"Manually corrected routing from {current_stakeholders} to {correct_stakeholders}"
        )
        
        # Add to correction manager
        self.correction_manager.add_correction(correction)
        
        # Update the trace
        self.trace_manager.add_decision(
            fingerprint,
            DecisionType.OVERRIDE,
            "AlertDebugger",
            notes=reason,
            input_state={"original_stakeholders": current_stakeholders},
            output_state={"corrected_stakeholders": correct_stakeholders},
            metadata={"corrected_by": corrected_by}
        )
        
        return {"status": "success", "correction_id": correction.id}
    
    def correct_fingerprint(
        self,
        original_fingerprint: str,
        corrected_fingerprint: str,
        reason: str,
        corrected_by: str
    ) -> Dict:
        """Correct a fingerprint misclassification"""
        trace = self.trace_manager.get_trace(original_fingerprint)
        if not trace:
            return {"error": "Trace not found for fingerprint"}
            
        # Create correction record
        correction = AlertCorrection(
            alert_fingerprint=original_fingerprint,
            corrected_by=corrected_by,
            correction_time=datetime.now(),
            original_trace_id=trace.trace_id,
            reason=reason,
            correction_type="fingerprint",
            from_value=original_fingerprint,
            to_value=corrected_fingerprint,
            notes=f"Corrected fingerprint from {original_fingerprint} to {corrected_fingerprint}"
        )
        
        # Add to correction manager
        self.correction_manager.add_correction(correction)
        
        # Update the trace
        self.trace_manager.add_decision(
            original_fingerprint,
            DecisionType.FINGERPRINT_CLASSIFICATION,
            "AlertDebugger",
            notes=reason,
            input_state={"original_fingerprint": original_fingerprint},
            output_state={"corrected_fingerprint": corrected_fingerprint},
            metadata={"corrected_by": corrected_by},
            success=False,
            error="Fingerprint misclassification"
        )
        
        return {"status": "success", "correction_id": correction.id}
    
    def _find_similar_traces(self, trace: RoutingTrace) -> List[Dict]:
        """Find similar traces with different routing outcomes"""
        service = trace.service
        anomaly_type = trace.anomaly_type
        
        similar_traces = []
        
        for other_trace in self.trace_manager.traces.values():
            if other_trace.trace_id == trace.trace_id:
                continue
                
            if other_trace.service == service and other_trace.anomaly_type == anomaly_type:
                stakeholder_intersection = trace.stakeholders_notified.intersection(
                    other_trace.stakeholders_notified
                )
                stakeholder_difference = (
                    trace.stakeholders_notified.symmetric_difference(
                        other_trace.stakeholders_notified
                    )
                )
                
                if stakeholder_difference:
                    similar_traces.append({
                        "trace_id": other_trace.trace_id,
                        "fingerprint": other_trace.alert_fingerprint,
                        "confidence": other_trace.confidence,
                        "stakeholders_notified": list(other_trace.stakeholders_notified),
                        "stakeholder_intersection": list(stakeholder_intersection),
                        "stakeholder_difference": list(stakeholder_difference)
                    })
                    
        return similar_traces
        
    def _generate_explanation(
        self, trace: RoutingTrace, 
        failures: List[Dict], 
        corrections: List[AlertCorrection]
    ) -> Dict:
        """Generate an explanation for routing decisions or issues"""
        explanation = {
            "summary": "",
            "issues": [],
            "decision_factors": []
        }
        
        # Check for failures
        if failures:
            explanation["summary"] = f"Alert experienced {len(failures)} failures during processing"
            for failure in failures:
                explanation["issues"].append({
                    "component": failure["component"],
                    "error": failure["error"],
                    "timestamp": failure["timestamp"]
                })
        
        # Check for corrections
        elif corrections:
            explanation["summary"] = f"Alert routing was manually corrected {len(corrections)} times"
            for correction in corrections:
                explanation["issues"].append({
                    "correction_type": correction.correction_type,
                    "reason": correction.reason,
                    "from": correction.from_value, 
                    "to": correction.to_value
                })
        
        # Normal routing case
        else:
            explanation["summary"] = "Alert was routed according to routing policies"
            
            # Extract key decision factors
            routing_decisions = [d for d in trace.decision_points 
                             if d.decision_type == DecisionType.ROUTING]
            stakeholder_decisions = [d for d in trace.decision_points
                                  if d.decision_type == DecisionType.STAKEHOLDER_SELECTION]
            
            for decision in routing_decisions + stakeholder_decisions:
                explanation["decision_factors"].append({
                    "component": decision["component"],
                    "rule_name": decision["rule_name"],
                    "input": decision["input_state"],
                    "output": decision["output_state"]
                })
            
        return explanation
        
    def _format_correction(self, correction: AlertCorrection) -> Dict:
        """Format a correction record for output"""
        return {
            "id": correction.id,
            "timestamp": correction.correction_time.isoformat(),
            "type": correction.correction_type,
            "corrected_by": correction.corrected_by,
            "reason": correction.reason,
            "from": correction.from_value,
            "to": correction.to_value,
            "notes": correction.notes
        }