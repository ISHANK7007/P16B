class DissentCollector:
    """
    Collects and aggregates dissent from personas
    about constraint overrides.
    """
    def __init__(self, dissent_registry=None):
        self.dissent_registry = dissent_registry or DissentRegistry()
        
    def collect_dissent(self, mutation_id, personas, constraint_results, session_context):
        """
        Collect dissent from multiple personas about a mutation
        Returns collected dissent reports
        """
        collected_reports = []
        
        for persona in personas:
            # Check if persona wants to dissent
            dissent_data = persona.evaluate_override(mutation_id, constraint_results)
            
            if dissent_data and dissent_data.get("dissent", False):
                # Create dissent report
                report = PersonaDissent(
                    persona_id=persona.id,
                    persona_role=persona.role,
                    dissent_score=dissent_data.get("score", 0.5),
                    metadata=dissent_data.get("metadata")
                )
                
                # Add specific objections
                for objection in dissent_data.get("objections", []):
                    report.add_objection(
                        constraint_id=objection.get("constraint_id"),
                        severity=objection.get("severity", 0.5),
                        reason=objection.get("reason", "")
                    )
                    
                # Register in the registry
                self.dissent_registry.register_dissent(
                    mutation_id,
                    report,
                    session_context
                )
                
                collected_reports.append(report)
                
        return collected_reports