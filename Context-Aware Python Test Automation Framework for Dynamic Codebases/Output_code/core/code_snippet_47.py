class RegressionDetector:
    """
    Detects regressions in output quality based on fingerprinted prompt paths
    and enables automatic rollback to known good states.
    """
    def __init__(self, cursor):
        self.cursor = cursor
        self.regression_history = []
        self.known_good_paths = {}  # Maps fingerprints to success ratings
        self.known_bad_paths = {}   # Maps fingerprints to failure types
        
    def register_successful_path(self, fingerprint, quality_score=1.0):
        """Register a successful prompt path"""
        fingerprint_id = fingerprint["fingerprint"]
        
        self.known_good_paths[fingerprint_id] = {
            "fingerprint": fingerprint,
            "quality_score": quality_score,
            "usage_count": self.known_good_paths.get(fingerprint_id, {}).get("usage_count", 0) + 1,
            "last_used": time.time()
        }
        
    def register_regression(self, fingerprint, regression_type, severity=1.0):
        """Register a regression for this prompt path"""
        fingerprint_id = fingerprint["fingerprint"]
        
        regression = {
            "fingerprint": fingerprint,
            "type": regression_type,
            "severity": severity,
            "timestamp": time.time()
        }
        
        self.regression_history.append(regression)
        
        # Update known bad paths
        if fingerprint_id not in self.known_bad_paths:
            self.known_bad_paths[fingerprint_id] = []
            
        self.known_bad_paths[fingerprint_id].append(regression)
        
        return regression
        
    def check_path_quality(self, fingerprint):
        """Check if a path is known good, bad, or unknown"""
        fingerprint_id = fingerprint["fingerprint"]
        
        if fingerprint_id in self.known_good_paths:
            return {
                "status": "good",
                "quality_score": self.known_good_paths[fingerprint_id]["quality_score"],
                "confidence": min(1.0, self.known_good_paths[fingerprint_id]["usage_count"] / 10)
            }
            
        if fingerprint_id in self.known_bad_paths:
            regressions = self.known_bad_paths[fingerprint_id]
            worst_regression = max(regressions, key=lambda r: r["severity"])
            
            return {
                "status": "bad",
                "regression_type": worst_regression["type"],
                "severity": worst_regression["severity"],
                "confidence": min(1.0, len(regressions) / 5)
            }
            
        return {"status": "unknown"}
        
    def find_safe_rollback_point(self):
        """Find the nearest safe point to roll back to"""
        checkpoints = sorted(
            self.cursor.checkpoints.values(),
            key=lambda c: c["position"],
            reverse=True  # Most recent first
        )
        
        for checkpoint in checkpoints:
            fingerprint = checkpoint["fingerprint"]
            quality = self.check_path_quality(fingerprint)
            
            if quality["status"] == "good" and quality["confidence"] > 0.7:
                return checkpoint["checkpoint_id"]
                
        return None
        
    async def auto_rollback_on_regression(self, regression_detector, min_severity=0.7):
        """Automatically roll back to safe point if regression detected"""
        # Check if a regression is detected
        current_fingerprint = self.cursor.current_fingerprint
        quality = self.check_path_quality(current_fingerprint)
        
        if quality["status"] == "bad" and quality["severity"] >= min_severity:
            # Find safe rollback point
            safe_point = self.find_safe_rollback_point()
            
            if safe_point:
                # Perform rollback
                success, result = self.cursor.rollback_to_checkpoint(safe_point)
                
                if success:
                    return {
                        "rolled_back": True,
                        "checkpoint_id": safe_point,
                        "reason": quality["regression_type"]
                    }
                    
        return {"rolled_back": False}