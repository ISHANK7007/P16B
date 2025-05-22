class ActiveMitigationValidator:
    """Performs active testing to validate mitigation effectiveness"""
    
    async def validate_with_active_testing(self, validation_ctx, mitigation_record):
        """Use active testing methods to validate mitigation"""
        
        # Only proceed if active testing is allowed
        if not mitigation_record.allow_active_testing:
            return {"active_testing": "SKIPPED", "reason": "Not allowed for this mitigation"}
            
        active_tests = []
        
        # Determine which systems to test based on symptoms and mitigation
        test_targets = self._identify_test_targets(validation_ctx, mitigation_record)
        
        for target in test_targets:
            # Choose appropriate test method for this target
            test_method = self._select_test_method(target, mitigation_record)
            
            # Execute the test
            if test_method == "SYNTHETIC_TRANSACTION":
                test_result = await self._run_synthetic_transaction(target)
            elif test_method == "COMPONENT_TEST":
                test_result = await self._run_component_test(target)
            elif test_method == "LOAD_TEST":
                test_result = await self._run_mini_load_test(target)
            else:
                test_result = await self._run_health_check(target)
                
            active_tests.append({
                "target": target,
                "method": test_method,
                "result": test_result,
                "validates_mitigation": self._assess_test_relevance(
                    test_result, 
                    mitigation_record
                )
            })
            
        # Determine overall validation from test results
        validation_result = self._calculate_active_test_validation(active_tests)
        
        return {
            "active_testing": "COMPLETED",
            "tests": active_tests,
            "overall_result": validation_result
        }