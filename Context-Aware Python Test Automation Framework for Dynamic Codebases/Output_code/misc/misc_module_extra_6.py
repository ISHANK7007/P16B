def export_markdown_trace(audit_trace: MutationAuditTrace) -> str:
    """Export mutation trace in Markdown format for human review"""
    md_lines = [
        f"# Prompt Mutation Audit: {audit_trace.session_id}",
        f"**Generated:** {audit_trace.start_time.isoformat()}",
        f"**Format:** {audit_trace.prompt_format.name}",
        "",
        "## Original Prompt",
        "```",
        audit_trace.final_mutation.original,
        "```",
        "",
        "## Final Prompt",
        "```",
        audit_trace.final_mutation.mutated,
        "```",
        "",
        f"**Rationale:** {audit_trace.final_mutation.mutation_rationale}",
        "",
        "## Mutation Timeline",
        ""
    ]
    
    # Add timeline of events
    for i, event in enumerate(sorted(audit_trace.events, key=lambda e: e.timestamp)):
        md_lines.extend([
            f"### Event {i+1}: {event.event_type}",
            f"**Time:** {event.timestamp.isoformat()}",
            f"**Component:** {event.component}",
            f"**Details:** {_format_event_details(event.details)}",
            ""
        ])
        
    # Add persona contributions
    md_lines.extend([
        "## Persona Contributions",
        ""
    ])
    
    for persona in audit_trace.persona_involved:
        persona_events = [e for e in audit_trace.events if e.persona == persona]
        md_lines.extend([
            f"### {persona.name}",
            f"**Event count:** {len(persona_events)}",
            f"**Primary contributions:** {_summarize_persona_contribution(persona_events)}",
            ""
        ])
        
    return "\n".join(md_lines)