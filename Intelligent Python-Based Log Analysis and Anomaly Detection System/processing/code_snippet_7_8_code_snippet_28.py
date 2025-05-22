class AnomalyReclassificationService:
    """Service for reclassifying anomalies based on new evidence"""
    
    def __init__(self, anomaly_store, fingerprint_registry, ml_service):
        self.anomaly_store = anomaly_store
        self.fingerprint_registry = fingerprint_registry
        self.ml_service = ml_service
        self.feedback_collector = FeedbackCollector()
        
    async def evaluate_reclassification(self, anomaly_fingerprint):
        """Evaluate if an anomaly should be reclassified based on new data"""
        # Get anomaly details
        anomaly_records = await self.anomaly_store.get_by_fingerprint(anomaly_fingerprint)
        
        if not anomaly_records:
            return None
            
        # Get feedback on this fingerprint
        feedback = await self.feedback_collector.get_feedback(anomaly_fingerprint)
        
        # Get similar resolved anomalies
        similar_resolved = await self.fingerprint_registry.get_similar_resolved(
            anomaly_fingerprint
        )
        
        # Build feature vector for ML evaluation
        features = self._build_reclassification_features(
            anomaly_records, 
            feedback, 
            similar_resolved
        )
        
        # Get ML prediction on benign probability
        prediction = await self.ml_service.predict_benign_probability(features)
        
        if prediction.probability >= 0.95:
            # High confidence this is benign
            return ReclassificationResult(
                fingerprint=anomaly_fingerprint,
                new_classification="benign",
                confidence=prediction.probability,
                evidence={
                    "ml_classification": {
                        "probability": prediction.probability,
                        "model_version": prediction.model_version,
                        "feature_importance": prediction.feature_importance
                    },
                    "human_feedback": {
                        "false_positive_reports": len(feedback.get("false_positive", [])),
                        "confirmation_reports": len(feedback.get("confirmed", []))
                    },
                    "similar_patterns": {
                        "count": len(similar_resolved),
                        "resolution_types": self._count_resolution_types(similar_resolved)
                    }
                }
            )
        
        return None
    
    def _build_reclassification_features(self, anomalies, feedback, similar_resolved):
        """Build feature vector for reclassification ML model"""
        # Extract features from anomalies, feedback, and similar cases
        # Return structured feature vector
        pass
        
    def _count_resolution_types(self, resolutions):
        """Count different resolution types from similar resolved anomalies"""
        counts = {}
        for resolution in resolutions:
            res_type = resolution.resolution_type
            counts[res_type] = counts.get(res_type, 0) + 1
        return counts