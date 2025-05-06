class DissentRegistry:
    """
    Central registry for tracking persona dissent across sessions
    with persistence and retrieval capabilities.
    """
    def __init__(self, decay_manager=None):
        self.dissent_records = {}  # Maps mutation_id to list of dissent reports
        self.persona_history = {}  # Maps persona_id to dissent history
        self.session_records = {}  # Maps session_id to dissent summary
        self.decay_manager = decay_manager or DissentDecayManager()
        
    def register_dissent(self, mutation_id, dissent_report, session_context):
        """
        Register a new dissent report for a mutation
        Links it to the current session and persona history
        """
        # Set session ID on the report
        dissent_report.session_id = session_context.session_id
        
        # Add to mutation records
        if mutation_id not in self.dissent_records:
            self.dissent_records[mutation_id] = []
        self.dissent_records[mutation_id].append(dissent_report)
        
        # Add to persona history
        persona_id = dissent_report.persona_id
        if persona_id not in self.persona_history:
            self.persona_history[persona_id] = []
        self.persona_history[persona_id].append({
            "mutation_id": mutation_id,
            "dissent_report": dissent_report,
            "timestamp": time.time()
        })
        
        # Add to session records
        session_id = session_context.session_id
        if session_id not in self.session_records:
            self.session_records[session_id] = {
                "dissent_counts": {},
                "total_dissent": 0,
                "persona_activity": {}
            }
            
        # Update session summary
        session_rec = self.session_records[session_id]
        if persona_id not in session_rec["dissent_counts"]:
            session_rec["dissent_counts"][persona_id] = 0
            session_rec["persona_activity"][persona_id] = []
            
        session_rec["dissent_counts"][persona_id] += 1
        session_rec["total_dissent"] += 1
        session_rec["persona_activity"][persona_id].append({
            "mutation_id": mutation_id,
            "dissent_score": dissent_report.dissent_score,
            "timestamp": time.time()
        })
        
        return True
        
    def get_dissent_reports(self, mutation_id, apply_decay=True, session_context=None):
        """
        Get all dissent reports for a mutation
        Optionally applies decay based on session hops
        """
        if mutation_id not in self.dissent_records:
            return []
            
        reports = self.dissent_records[mutation_id]
        
        if apply_decay and session_context:
            # Apply decay based on session hops
            reports = self.decay_manager.apply_decay(reports, session_context)
            
        return reports
        
    def get_persona_dissent_history(self, persona_id, limit=None):
        """Get dissent history for a specific persona"""
        if persona_id not in self.persona_history:
            return []
            
        history = self.persona_history[persona_id]
        
        # Sort by timestamp (newest first)
        sorted_history = sorted(history, key=lambda x: x["timestamp"], reverse=True)
        
        if limit is not None:
            return sorted_history[:limit]
        return sorted_history
        
    def get_session_dissent_summary(self, session_id):
        """Get summary of dissent activity in a session"""
        if session_id not in self.session_records:
            return {"dissent_counts": {}, "total_dissent": 0, "persona_activity": {}}
        return self.session_records[session_id]