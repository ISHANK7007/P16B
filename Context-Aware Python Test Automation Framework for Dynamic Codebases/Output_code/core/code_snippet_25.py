class CoherenceDebugger:
    """
    Debugging system for analyzing and fixing coherence failures in streaming sessions
    """
    def __init__(self, cursor):
        self.cursor = cursor
        self.violation_log = []
        self.trace_context = {}
        self.active_debug_session = None
        
    def start_debug_session(self, violation=None):
        """Start a debug session, optionally focusing on a specific violation"""
        self.active_debug_session = {
            "id": str(uuid.uuid4()),
            "start_time": time.time(),
            "focus_violation": violation,
            "checkpoint_state": self._capture_current_state(),
            "remediation_attempts": []
        }
        return self.active_debug_session["id"]
        
    def analyze_violation(self, violation):
        """Deep analysis of a coherence violation to determine root causes"""
        # Record violation in log
        self.violation_log.append(violation)
        
        analysis = {
            "violation": violation,
            "token_context": self._extract_token_context(violation),
            "edit_history": self._extract_relevant_edits(violation),
            "potential_causes": self._identify_potential_causes(violation),
            "remediation_options": self._generate_remediation_options(violation)
        }
        
        # For instruction drift, add semantic analysis
        if violation.type == "instruction_drift":
            analysis["semantic_trajectory"] = self._analyze_semantic_trajectory(violation)
            
        # For structural issues, add structure analysis
        if violation.type in ["abandoned_quote", "unclosed_code_block", "list_incoherence"]:
            analysis["structure_trace"] = self._analyze_structure_evolution(violation)
            
        return analysis
        
    def apply_remediation(self, remediation_option):
        """Apply a remediation option to fix a coherence issue"""
        if not self.active_debug_session:
            raise ValueError("No active debug session")
            
        # Record the attempt
        self.active_debug_session["remediation_attempts"].append({
            "option": remediation_option,
            "timestamp": time.time(),
            "pre_state": self._capture_current_state()
        })
        
        # Apply the remediation
        if remediation_option["type"] == "edit_patch":
            # Apply an edit patch
            result = self.cursor.apply_edit(remediation_option["patch"])
            
        elif remediation_option["type"] == "rewind_and_regenerate":
            # Rewind to a checkpoint and restart generation
            rewind_pos = remediation_option["rewind_position"]
            success, state = self.cursor.rewind_to(rewind_pos)
            
            if success:
                # Apply any specified modifications before continuing
                if "modifications" in remediation_option:
                    for modification in remediation_option["modifications"]:
                        self.cursor.apply_edit(modification)
                
        elif remediation_option["type"] == "constraint_injection":
            # Add a constraint to prevent similar issues
            constraint = remediation_option["constraint"]
            self.cursor.add_constraint(constraint)
            
        # Update the remediation attempt with result
        latest_attempt = self.active_debug_session["remediation_attempts"][-1]
        latest_attempt["post_state"] = self._capture_current_state()
        latest_attempt["success"] = self._evaluate_remediation_success(
            latest_attempt["pre_state"], latest_attempt["post_state"], remediation_option)
            
        return latest_attempt
        
    def _capture_current_state(self):
        """Capture current cursor state for comparison"""
        return {
            "position": self.cursor.current_position,
            "token_history": self.cursor.token_history[-100:],
            "active_constraints": [c.to_dict() for c in self.cursor.prompt_state.constraints],
            "semantic_context": self._get_current_semantic_context(),
            "violation_count": len(self.violation_log)
        }
        
    def _evaluate_remediation_success(self, pre_state, post_state, remediation):
        """Evaluate if a remediation attempt was successful"""
        # If no new violations of the same type have occurred
        violation_type = remediation.get("target_violation_type")
        if violation_type:
            new_violations = [v for v in self.violation_log 
                             if v.timestamp > pre_state["timestamp"] 
                             and v.type == violation_type]
            if not new_violations:
                return True
                
        # For specific remediation types, check other success criteria
        if remediation["type"] == "constraint_injection":
            # Check if constraint is being satisfied
            constraint = remediation["constraint"]
            return self._check_constraint_satisfaction(constraint, post_state["token_history"])
            
        return False