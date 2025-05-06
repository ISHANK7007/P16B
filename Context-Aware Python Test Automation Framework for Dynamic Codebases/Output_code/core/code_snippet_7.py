# Initialize the system
manager = LiveEditSessionManager()

# Create a new editing session
session_id = manager.create_session(
    prompt_template="Write a story about a {protagonist} who {action}.",
    initial_constraints=[
        StreamConstraint("prevent", "violent content"),
        StreamConstraint("ensure", "happy ending")
    ]
)

# Start streaming with initial parameters
response_stream = start_streaming_completion(
    session=manager.active_sessions[session_id],
    parameters={"protagonist": "cat", "action": "learns to swim"}
)

# Later, during streaming, apply an edit
patch_id = manager.apply_edit(
    session_id=session_id,
    edit_operation={
        "type": "replace",
        "pattern": "cat",
        "replacement": "brave little cat",
        "apply_to_future": True  # Affects future token generation
    }
)

# Add a constraint mid-stream
manager.add_constraint(
    session_id=session_id,
    constraint=StreamConstraint(
        "transform", 
        "swimming", 
        "gracefully swimming",
        priority=2
    )
)