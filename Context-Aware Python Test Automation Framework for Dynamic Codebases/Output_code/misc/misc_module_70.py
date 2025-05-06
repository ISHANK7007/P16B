class DissentReporter:
    """
    Generates reports and visualizations of persona dissent
    for transparency and analysis.
    """
    def __init__(self, dissent_registry=None):
        self.dissent_registry = dissent_registry or DissentRegistry()
        
    def generate_dissent_report(self, mutation_id, session_context=None):
        """
        Generate a comprehensive report on dissent for a mutation
        Includes dissent scores, objections, and decay analysis
        """
        # Get raw dissent reports
        raw_reports = self.dissent_registry.get_dissent_reports(
            mutation_id,
            apply_decay=False
        )
        
        # If session context provided, also get decay-adjusted reports
        decayed_reports = None
        if session_context:
            decayed_reports = self.dissent_registry.get_dissent_reports(
                mutation_id,
                apply_decay=True,
                session_context=session_context
            )
            
        # Build the report
        report = {
            "mutation_id": mutation_id,
            "timestamp": time.time(),
            "total_dissent_count": len(raw_reports),
            "dissent_by_role": self._group_by_role(raw_reports),
            "top_objections": self._extract_top_objections(raw_reports),
            "comprehensive_data": {
                "raw": [r.to_dict() for r in raw_reports]
            }
        }
        
        # Add decay analysis if available
        if decayed_reports:
            report["decay_analysis"] = self._analyze_decay(raw_reports, decayed_reports)
            report["comprehensive_data"]["decayed"] = [r.to_dict() for r in decayed_reports]
            report["effective_dissent_score"] = self._calculate_effective_score(decayed_reports)
            
        return report
        
    def _group_by_role(self, dissent_reports):
        """Group dissent reports by persona role"""
        by_role = {}
        
        for report in dissent_reports:
            role = report.persona_role
            if role not in by_role:
                by_role[role] = {
                    "count": 0,
                    "average_score": 0,
                    "reports": []
                }
                
            by_role[role]["count"] += 1
            by_role[role]["reports"].append(report)
            
        # Calculate average scores
        for role, data in by_role.items():
            if data["count"] > 0:
                total = sum(r.dissent_score for r in data["reports"])
                data["average_score"] = total / data["count"]
                
        return by_role
        
    def _extract_top_objections(self, dissent_reports):
        """Extract the most common objections"""
        objection_counts = {}
        
        for report in dissent_reports:
            for objection in report.objections:
                constraint_id = objection.get("constraint_id")
                if constraint_id not in objection_counts:
                    objection_counts[constraint_id] = {
                        "count": 0,
                        "total_severity": 0,
                        "reasons": []
                    }
                    
                objection_counts[constraint_id]["count"] += 1
                objection_counts[constraint_id]["total_severity"] += objection.get("severity", 0.5)
                objection_counts[constraint_id]["reasons"].append(objection.get("reason", ""))
                
        # Calculate average severity and sort
        top_objections = []
        for constraint_id, data in objection_counts.items():
            avg_severity = data["total_severity"] / data["count"] if data["count"] > 0 else 0
            top_objections.append({
                "constraint_id": constraint_id,
                "count": data["count"],
                "average_severity": avg_severity,
                "sample_reasons": data["reasons"][:3]  # Just include a few examples
            })
            
        # Sort by count, then severity
        return sorted(
            top_objections, 
            key=lambda x: (x["count"], x["average_severity"]),
            reverse=True
        )
        
    def _analyze_decay(self, raw_reports, decayed_reports):
        """Analyze the effect of decay on dissent reports"""
        raw_by_id = {r.persona_id: r for r in raw_reports}
        decayed_by_id = {r.persona_id: r for r in decayed_reports}
        
        decay_analysis = {
            "total_decay_effect": 0,
            "persona_decay": []
        }
        
        # Calculate total decay effect
        if raw_reports:
            raw_total = self._calculate_effective_score(raw_reports)
            decayed_total = self._calculate_effective_score(decayed_reports)
            decay_analysis["total_decay_effect"] = 1 - (decayed_total / raw_total) if raw_total > 0 else 0
            
        # Calculate per-persona decay
        for persona_id, raw in raw_by_id.items():
            if persona_id in decayed_by_id:
                decayed = decayed_by_id[persona_id]
                
                decay_percent = 1 - (decayed.persona_weight / raw.persona_weight)
                
                decay_analysis["persona_decay"].append({
                    "persona_id": persona_id,
                    "role": raw.persona_role,
                    "original_weight": raw.persona_weight,
                    "decayed_weight": decayed.persona_weight,
                    "decay_percent": decay_percent
                })
                
        return decay_analysis
        
    def _calculate_effective_score(self, dissent_reports):
        """Calculate the effective dissent score from reports"""
        if not dissent_reports:
            return 0.0
            
        total_weight = 0.0
        weighted_sum = 0.0
        
        for report in dissent_reports:
            weight = report.persona_weight
            total_weight += weight
            weighted_sum += report.dissent_score * weight
            
        if total_weight > 0:
            return weighted_sum / total_weight
        return 0.0