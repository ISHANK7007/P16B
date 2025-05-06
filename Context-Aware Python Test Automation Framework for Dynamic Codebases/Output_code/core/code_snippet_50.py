# Initialize the session manager
manager = LiveEditSessionManager()

# Create session with validation
session_id = manager.create_session("Write about climate change.")
cursor = manager.initialize_cursor_with_validation(
    session_id, "Write about climate change.")

# Start generation and register initial checkpoint
initial_checkpoint = cursor.register_checkpoint()

# Start streaming response
streaming_task = asyncio.create_task(
    manager.generate_stream(session_id)
)

# After generation has started, an edit is requested
edit_operation = EditOperation(
    operation_type="replace",
    position=12,
    content="global warming",
    old_content="climate change"
)

try:
    # Apply edit - validation happens automatically
    result = cursor.apply_edit(edit_operation)
    print(f"Edit applied successfully with checkpoint {result.get('checkpoint_id')}")
    
except EditValidationError as e:
    # Handle validation failure
    print(f"Edit validation failed: {e}")
    print(f"Validation results: {e.validation_results}")
    
    # Suggest alternatives
    alternatives = manager.suggest_alternative_edits(
        session_id, edit_operation, e.validation_results)
    print(f"Try these instead: {alternatives}")

# Later, if regression is detected
quality_issue = cursor.event_bus.wait_for_event("coherence_violation")
if quality_issue:
    # Register as regression
    regression = session.regression_detector.register_regression(
        cursor.current_fingerprint,
        quality_issue["violation"].type,
        quality_issue["violation"].severity
    )
    
    # Find safe rollback point
    safe_point = session.regression_detector.find_safe_rollback_point()
    
    if safe_point:
        # Roll back to safe point
        success, result = cursor.rollback_to_checkpoint(safe_point)
        if success:
            print(f"Rolled back to checkpoint {safe_point} due to {regression['type']}")