async def _generate_causal_explanation(self, enhanced_record):
    # Prepare context for LLM
    context = {
        "service_context": enhanced_record.service_context,
        "anomaly_details": enhanced_record.anomaly_context,
        "root_causes": enhanced_record.root_cause_references,
        "causal_path": enhanced_record.causal_path,
        "historical_incidents": self._fetch_similar_incidents(enhanced_record)
    }
    
    # Generate explanation prompt
    prompt = self._construct_causal_explanation_prompt(context)
    
    # Query LLM for explanation and confidence
    llm_response = await self.llm_service.generate_structured_response(
        prompt=prompt,
        response_schema={
            "reasoning": "string",
            "confidence_score": "float",
            "alternative_explanations": "array",
            "verification_steps": "array"
        }
    )
    
    # Apply calibration to raw confidence score
    calibrated_confidence = self._calibrate_confidence_score(
        llm_response.confidence_score,
        enhanced_record.anomaly_context
    )
    
    return CausalExplanation(
        reasoning=llm_response.reasoning,
        confidence_score=calibrated_confidence,
        alternative_explanations=llm_response.alternative_explanations,
        verification_steps=llm_response.verification_steps
    )