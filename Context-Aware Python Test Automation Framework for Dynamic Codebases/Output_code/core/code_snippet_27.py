class CoherenceMonitoringDashboard:
    """Dashboard for real-time monitoring of coherence issues"""
    def __init__(self, validator, debugger):
        self.validator = validator
        self.debugger = debugger
        self.active_violations = {}
        self.stats = {
            "total_violations": 0,
            "by_type": {},
            "by_severity": {
                "low": 0,
                "medium": 0,
                "high": 0,
                "critical": 0
            }
        }
        
    def update(self, new_violations):
        """Update dashboard with new violations"""
        for violation in new_violations:
            self.stats["total_violations"] += 1
            
            # Update by type
            self.stats["by_type"][violation.type] = \
                self.stats["by_type"].get(violation.type, 0) + 1
                
            # Update by severity
            severity_level = self._categorize_severity(violation.severity)
            self.stats["by_severity"][severity_level] += 1
            
            # Add to active violations if critical or high
            if severity_level in ["critical", "high"]:
                self.active_violations[violation.id] = violation
                
        # Remove resolved violations
        to_remove = []
        for vid, violation in self.active_violations.items():
            if violation.is_resolved:
                to_remove.append(vid)
                
        for vid in to_remove:
            del self.active_violations[vid]
            
    def get_status_summary(self):
        """Get a summary of the current coherence status"""
        return {
            "active_critical_violations": len([v for v in self.active_violations.values() 
                                             if self._categorize_severity(v.severity) == "critical"]),
            "total_violations": self.stats["total_violations"],
            "most_common_type": max(self.stats["by_type"].items(), 
                                   key=lambda x: x[1])[0] if self.stats["by_type"] else None,
            "severity_distribution": self.stats["by_severity"]
        }
        
    def _categorize_severity(self, severity_value):
        """Categorize a severity value into a level"""
        if severity_value < 0.3:
            return "low"
        elif severity_value < 0.6:
            return "medium"
        elif severity_value < 0.9:
            return "high"
        else:
            return "critical"