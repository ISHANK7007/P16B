class IncidentSimulator:
    """Framework for simulating complex incidents with evolving alert patterns"""
    
    def __init__(self, sandbox):
        self.sandbox = sandbox
        self.active_incidents = {}
        self.timelines = {}
        self.generators = {}
    
    async def start_incident(self, incident_template, context=None):
        """Start a new incident simulation"""
        # Generate incident ID
        incident_id = str(uuid.uuid4())
        
        # Load incident template
        template = await self._load_incident_template(incident_template)
        
        # Create timeline
        timeline = self._create_timeline(template, context)
        self.timelines[incident_id] = timeline
        
        # Create anomaly generator for this incident
        self.generators[incident_id] = SyntheticAnomalyGenerator()
        
        # Record incident
        self.active_incidents[incident_id] = {
            "id": incident_id,
            "template": template["name"],
            "start_time": datetime.utcnow().isoformat(),
            "context": context or {},
            "phase": "initial",
            "anomalies": [],
            "alerts": [],
            "current_step": 0
        }
        
        # Execute first phase
        await self._execute_next_step(incident_id)
        
        return incident_id
    
    async def advance_incident(self, incident_id):
        """Advance incident to next phase"""
        if incident_id not in self.active_incidents:
            raise ValueError(f"Unknown incident: {incident_id}")
            
        # Execute next phase
        await self._execute_next_step(incident_id)
        
        return self.active_incidents[incident_id]
    
    async def get_incident_status(self, incident_id):
        """Get current status of an incident"""
        if incident_id not in self.active_incidents:
            raise ValueError(f"Unknown incident: {incident_id}")
            
        return self.active_incidents[incident_id]
    
    async def _execute_next_step(self, incident_id):
        """Execute the next step in the incident timeline"""
        incident = self.active_incidents[incident_id]
        timeline = self.timelines[incident_id]
        
        # Check if we've reached the end
        if incident["current_step"] >= len(timeline):
            incident["phase"] = "completed"
            return incident
        
        # Get next step
        step = timeline[incident["current_step"]]
        incident["phase"] = step["phase"]
        
        # Execute step based on type
        if step["type"] == "anomaly":
            # Generate and inject anomaly
            result = await self.sandbox.inject_anomaly(
                step["anomaly_template"],
                context=step.get("context")
            )
            
            incident["anomalies"].append({
                "id": result["anomaly"].id,
                "type": result["anomaly"].type.value,
                "service": result["anomaly"].service_name
            })
            
            incident["alerts"].append({
                "id": result["alert"]["id"],
                "trace_id": result["trace_id"]
            })
            
        elif step["type"] == "team_action":
            # Simulate team action
            alert_id = incident["alerts"][-1]["id"]
            await self.sandbox.simulate_team_action(
                alert_id,
                step["team_id"],
                step["action"],
                metadata=step.get("metadata")
            )
            
        elif step["type"] == "time_advance":
            # Advance time
            await self.sandbox.time_controller.advance(
                timedelta(seconds=step["seconds"])
            )
            
        # Increment step counter
        incident["current_step"] += 1
        
        # Check for auto-advance
        if step.get("auto_advance", False) and incident["current_step"] < len(timeline):
            await self._execute_next_step(incident_id)
            
        return incident
    
    def _create_timeline(self, template, context):
        """Create a concrete timeline from template and context"""
        timeline = []
        
        # Process each phase
        for phase in template["phases"]:
            phase_name = phase["name"]
            
            # Add each step in phase
            for step in phase["steps"]:
                timeline_step = {
                    "phase": phase_name,
                    "type": step["type"],
                    **step  # Include all step properties
                }
                
                # Apply context overrides if any
                if context and "step_overrides" in context:
                    step_id = step.get("id")
                    if step_id and step_id in context["step_overrides"]:
                        timeline_step.update(context["step_overrides"][step_id])
                        
                timeline.append(timeline_step)
                
        return timeline