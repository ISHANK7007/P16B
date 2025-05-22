async def _handle_partial_success(self, validation_result, mitigation_record):
    """Handle cases where mitigation partially resolved the symptoms"""
    
    # Calculate overall effectiveness percentage
    effectiveness = validation_result.checkpoints[-1]["resolution_percent"]
    
    # Determine if this is "good enough" based on configuration
    success_threshold = mitigation_record.partial_success_threshold or 0.85
    
    if effectiveness >= success_threshold:
        # Mark as successful but note it was partial
        validation_result.status = "PARTIAL_SUCCESS"
        validation_result.partial_success_percentage = effectiveness
        
        # Analyze remaining issues
        remaining_issues = await self._analyze_remaining_symptoms(
            validation_result.checkpoints[-1]["remaining_symptoms"]
        )
        
        # Create supplementary mitigation plan for remaining issues
        supplementary_plan = await self.advisor_module.generate_supplementary_mitigation(
            original_mitigation=mitigation_record,
            remaining_issues=remaining_issues,
            partial_success_context={
                "effectiveness": effectiveness,
                "resolved_symptoms": validation_result.resolved_symptoms,
                "remaining_symptoms": validation_result.checkpoints[-1]["remaining_symptoms"]
            }
        )
        
        validation_result.supplementary_plan = supplementary_plan
        
        return validation_result
    else:
        # Not good enough, treat as failure
        validation_result.status = "FAILED"
        validation_result.failure_reason = "INSUFFICIENT_RESOLUTION"
        return await self._handle_failed_validation(
            validation_result, 
            mitigation_record.checkpoint_id, 
            mitigation_record
        )