def _format_causal_explanation(self, llm_reasoning_trace):
    """Format the causal explanation with confidence indicators"""
    confidence_level = self._determine_confidence_level(record.causal_confidence_score)
    
    formatted_explanation = {
        "summary": llm_reasoning_trace[:200] + "...",
        "full_explanation": llm_reasoning_trace,
        "confidence_level": confidence_level,
        "confidence_indicators": {
            "historical_similarity": record.historical_match_score,
            "fingerprint_precision": record.fingerprint_confidence,
            "model_certainty": record.causal_confidence_score,
            "temporal_consistency": record.temporal_consistency_score
        },
        "verification_steps": self._generate_verification_steps(record)
    }
    
    return formatted_explanation