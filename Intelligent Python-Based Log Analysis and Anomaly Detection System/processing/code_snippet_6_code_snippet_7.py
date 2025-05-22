# Top-level routing function that integrates both direct routing and escalation
async def route_and_escalate_anomalies(
    anomalies: List[Anomaly],
    orchestrator: EnhancedRoutingOrchestrator,
    escalation_engine: EscalationPolicyEngine,
    suppression_engine: SuppressionEngine
) -> Dict[str, Any]:
    results = {
        "routed": [],
        "escalated": [],
        "suppressed": []
    }
    
    # First, route each anomaly
    for anomaly in anomalies:
        # Check suppression first
        is_suppressed, rule_id = suppression_engine.check_suppression(anomaly)
        if is_suppressed:
            results["suppressed"].append({
                "fingerprint": anomaly.fingerprint,
                "rule_id": rule_id
            })
            continue
            
        # Route the anomaly
        routing_result = await orchestrator.route_anomaly(anomaly)
        results["routed"].append(routing_result)
    
    # Then check for time-based escalations
    escalation_results = await escalation_engine.check_for_escalations()
    results["escalated"].extend(escalation_results)
    
    # Also check frequency-based escalations
    freq_escalations = await escalation_engine.check_frequency_based_escalations()
    results["escalated"].extend(freq_escalations)
    
    return results