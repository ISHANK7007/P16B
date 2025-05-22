def validate_semantics(ast):
    errors = []
    
    # Validate condition references
    for condition in ast.find_all_conditions():
        if condition.type == "property_access":
            if not is_valid_property_path(condition.property_path):
                errors.append(f"Invalid property path: {condition.property_path}")
    
    # Validate action parameters
    for action in ast.find_all_actions():
        if action.type == "escalate":
            if not is_valid_tier(action.tier):
                errors.append(f"Invalid escalation tier: {action.tier}")
        elif action.type == "notify":
            if not is_valid_channel(action.channel):
                errors.append(f"Unknown notification channel: {action.channel}")
    
    return ValidationResult(len(errors) == 0, errors=errors)