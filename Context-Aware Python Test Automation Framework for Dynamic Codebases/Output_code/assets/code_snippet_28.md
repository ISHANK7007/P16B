    def replace_invocation(match):
        capability_id = match.group(1)
        params_str = match.group(2).strip()
        
        # Parse parameters - this is a simplified version
        # In practice, would need proper parameter parsing
        params = {}
        if params_str:
            for param in params_str.split(","):
                if "=" in param:
                    key, value = param.split("=", 1)
                    params[key.strip()] = value.strip()
        
        # Execute capability
        success, result = self.execute_capability(
            capability_id, persona_id, params)
            
        # Record result
        results.append({
            "capability_id": capability_id,
            "success": success,
            "result": result
        })
        
        # Replace with result
        if success:
            return f"