    Authorized personas: {', '.join(authorized_personas)}
    """
    
    # Create scope with admin as owner
    scope_id, _ = self.coordinator.create_scope(
        content, "agent_capability", "admin")
        
    # Grant access to authorized personas
    for persona in authorized_personas:
        self.coordinator.grant_scope_access(
            persona, scope_id, AccessMode.READ | AccessMode.EXECUTE)
            
    capability["scope_id"] = scope_id
    self.capabilities[capability_id] = capability
    
    return capability_id

def authorize_persona(self, capability_id: str, persona_id: str) -> bool:
    """Authorize a persona to use a capability."""
    if capability_id not in self.capabilities:
        return False
        
    capability = self.capabilities[capability_id]
    capability["authorized_personas"].add(persona_id)
    
    return self.coordinator.grant_scope_access(
        persona_id, capability["scope_id"], AccessMode.READ | AccessMode.EXECUTE)

def revoke_authorization(self, capability_id: str, persona_id: str) -> bool:
    """Revoke a persona's authorization for a capability."""
    if capability_id not in self.capabilities:
        return False
        
    capability = self.capabilities[capability_id]
    if persona_id in capability["authorized_personas"]:
        capability["authorized_personas"].remove(persona_id)
        
    return self.coordinator.revoke_scope_access(
        persona_id, capability["scope_id"], AccessMode.EXECUTE)

def execute_capability(self, 
                     capability_id: str, 
                     persona_id: str, 
                     parameters: Dict[str, Any]) -> Tuple[bool, Any]:
    """Securely execute a capability if persona is authorized."""
    if capability_id not in self.capabilities:
        return False, "Capability not found"
        
    capability = self.capabilities[capability_id]
    
    # Check authorization
    if persona_id not in capability["authorized_personas"]:
        # Log security violation
        self.coordinator.handle_security_violation(
            persona_id,
            capability["scope_id"],
            "unauthorized_execution",
            f"Attempted unauthorized execution of capability {capability['name']}"
        )
        return False, "Not authorized"
        
    # Execute the capability function
    try:
        result = capability["function"](**parameters)
        return True, result
    except Exception as e:
        return False, f"Execution error: {str(e)}"

def process_invocations(self, 
                      text: str, 
                      persona_id: str) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Process all capability invocation tags in text.
    Returns processed text and execution results.
    """
    results = []
    
    # Find all invocation tags
    pattern = r"