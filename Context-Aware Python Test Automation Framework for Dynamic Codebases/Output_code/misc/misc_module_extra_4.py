def export_json_trace(audit_trace: MutationAuditTrace) -> str:
    """Export a complete mutation audit trace in JSON format"""
    return json.dumps({
        "session_id": audit_trace.session_id,
        "timestamp": audit_trace.start_time.isoformat(),
        "format": audit_trace.prompt_format.name,
        "personas": [p.name for p in audit_trace.persona_involved],
        "events": [_event_to_dict(e) for e in audit_trace.events],
        "mutations": {
            "original": audit_trace.final_mutation.original,
            "final": audit_trace.final_mutation.mutated,
            "rationale": audit_trace.final_mutation.mutation_rationale
        },
        "metadata": {
            "original_hash": _hash_text(audit_trace.final_mutation.original),
            "final_hash": _hash_text(audit_trace.final_mutation.mutated),
            "version": "1.0"
        }
    }, indent=2)