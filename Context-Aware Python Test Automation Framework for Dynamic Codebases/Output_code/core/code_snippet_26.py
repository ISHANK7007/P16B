class CoherenceVisualizationTools:
    """Tools for visualizing coherence issues and their context"""
    def __init__(self):
        self.renderers = {}
        
    def register_renderer(self, violation_type, renderer):
        """Register a specialized renderer for a violation type"""
        self.renderers[violation_type] = renderer
        
    def render_violation(self, violation, context):
        """Render a visualization of a coherence violation"""
        renderer = self.renderers.get(
            violation.type, self.renderers.get("default"))
            
        if not renderer:
            return self._basic_render(violation, context)
            
        return renderer(violation, context)
        
    def create_coherence_timeline(self, violations, token_stream, edits):
        """Create a timeline showing relationship between edits and violations"""
        timeline = []
        
        # Merge violations, tokens, and edits into timeline
        for violation in violations:
            timeline.append({
                "type": "violation",
                "timestamp": violation.timestamp,
                "data": violation
            })
            
        for edit in edits:
            timeline.append({
                "type": "edit",
                "timestamp": edit.timestamp,
                "data": edit
            })
            
        # Add significant token events
        for i, token in enumerate(token_stream):
            if token.metadata.get("is_significant"):
                timeline.append({
                    "type": "significant_token",
                    "timestamp": token.timestamp,
                    "data": token
                })
                
        # Sort by timestamp
        timeline.sort(key=lambda x: x["timestamp"])
        
        # Analyze causal connections
        self._analyze_causal_connections(timeline)
        
        return timeline
        
    def _analyze_causal_connections(self, timeline):
        """Analyze potential causal connections between edits and violations"""
        # For each violation, find preceding edits that might have caused it
        for i, event in enumerate(timeline):
            if event["type"] != "violation":
                continue
                
            violation = event["data"]
            preceding_edits = [
                e for e in timeline[:i] 
                if e["type"] == "edit" and 
                e["timestamp"] > violation.timestamp - 5.0  # Within 5 seconds
            ]
            
            if preceding_edits:
                event["potential_causes"] = preceding_edits