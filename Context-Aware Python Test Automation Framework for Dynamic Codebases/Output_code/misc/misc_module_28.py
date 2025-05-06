class VariableReuseDetector(ImplicitConstraintDetector):
    """
    Detects invalid variable reuse across dialogue turns
    """
    def __init__(self, backtrace_map, code_analyzer):
        super().__init__(backtrace_map)
        self.code_analyzer = code_analyzer
        
    def analyze(self, mutation, context):
        """Check for invalid variable reuse or redefinition"""
        violations = []
        
        # Get variables defined or modified by this mutation
        mutation_variables = self._extract_variables(mutation.new_text)
        
        # For each variable, check if it conflicts with existing variables
        for var_name, var_info in mutation_variables.items():
            # Check for variables with same name in prior context
            conflicts = self._find_variable_conflicts(var_name, mutation.turn_id, var_info)
            
            for conflict in conflicts:
                violations.append(
                    self.backtrace_map.record_violation(
                        span_id=mutation.new_span_id,
                        violation_type="invalid_variable_reuse",
                        description=f"Variable '{var_name}' conflicts with prior definition in turn {conflict['turn_id']}",
                        severity="medium" if conflict["is_redefinition"] else "high"
                    )
                )
                
        return violations
        
    def _extract_variables(self, text):
        """Extract variables defined or used in the text"""
        # Would use code analysis to extract variable definitions and usage
        # Return format: {var_name: {"type": type, "is_definition": bool}}
        return self.code_analyzer.extract_variables(text)
        
    def _find_variable_conflicts(self, var_name, current_turn_id, var_info):
        """Find variable conflicts with prior turns"""
        conflicts = []
        
        # Iterate through all spans in prior turns
        for span_id, span_data in self.backtrace_map.span_registry.items():
            if span_data.turn_id >= current_turn_id:
                continue  # Skip current/future turns
                
            # Extract variables from this prior span
            prior_variables = self._extract_variables(span_data.text)
            
            if var_name in prior_variables:
                prior_info = prior_variables[var_name]
                
                # Check for type incompatibility
                if prior_info.get("type") != var_info.get("type"):
                    conflicts.append({
                        "span_id": span_id,
                        "turn_id": span_data.turn_id,
                        "is_redefinition": True,
                        "type_mismatch": True
                    })
                    
                # Check if current usage is incompatible with prior definition
                elif prior_info.get("is_definition") and var_info.get("is_definition"):
                    conflicts.append({
                        "span_id": span_id,
                        "turn_id": span_data.turn_id,
                        "is_redefinition": True,
                        "type_mismatch": False
                    })
                    
                # Check if current usage would shadow a prior variable in a valid scope
                elif self._is_shadowing(span_id, var_name, current_turn_id):
                    conflicts.append({
                        "span_id": span_id,
                        "turn_id": span_data.turn_id,
                        "is_redefinition": False,
                        "is_shadowing": True
                    })
                    
        return conflicts
        
    def _is_shadowing(self, prior_span_id, var_name, current_turn_id):
        """Check if variable usage would shadow a prior definition"""
        # Implementation would analyze scope relationships
        pass