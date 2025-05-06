def export_sarif_trace(audit_trace: MutationAuditTrace) -> str:
    """Export mutation trace in SARIF format for IDE integration"""
    # Convert constraint violations to SARIF findings
    results = []
    for event in audit_trace.events:
        if event.event_type == "constraint_violation":
            results.append({
                "ruleId": event.details["constraint_name"],
                "message": {
                    "text": event.details["violation_description"]
                },
                "level": "error" if event.severity > 3 else "warning",
                "locations": [
                    {
                        "physicalLocation": {
                            "artifactLocation": {
                                "uri": f"prompt:{audit_trace.prompt_id}"
                            },
                            "region": {
                                "startLine": 1,
                                "startColumn": 1
                            }
                        }
                    }
                ]
            })
            
    return json.dumps({
        "version": "2.1.0",
        "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "PromptMutationValidator",
                        "informationUri": "https://github.com/yoursystem/prompt-mutation",
                        "rules": _get_constraint_rules(audit_trace)
                    }
                },
                "results": results
            }
        ]
    }, indent=2)