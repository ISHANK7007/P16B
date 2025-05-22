def validate_runtime(compiled_rule, validation_context):
    errors = []
    
    # Check for circular references
    if has_circular_dependencies(compiled_rule, validation_context.rule_registry):
        errors.append("Rule has circular dependencies")
    
    # Check for conflicting actions
    if has_conflicting_actions(compiled_rule.action_executor):
        errors.append("Rule contains conflicting actions")
    
    # Estimate performance impact
    performance_impact = estimate_performance_impact(compiled_rule)
    if performance_impact > validation_context.max_allowed_impact:
        errors.append(f"Rule exceeds performance budget: impact={performance_impact}")
    
    return ValidationResult(len(errors) == 0, errors=errors)