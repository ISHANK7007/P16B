# Initialize the session manager
manager = LiveEditSessionManager()
session_id = manager.create_session("Write about climate change solutions.")

# Initialize the cursor for bidirectional sync
cursor = manager.initialize_cursor(session_id, "Write about climate change solutions.")

# Start generation
generation_task = asyncio.create_task(
    manager.generate_stream(session_id)
)

# Agent observes initial tokens and decides to refine
# At this point, tokens "Climate change presents several challenges" have been generated
agent_decision = {
    "action": "refine_focus",
    "modification": {
        "type": "insert",
        "position": "after:challenges",
        "content": ", particularly in coastal regions,"
    },
    "reasoning": "Focusing on coastal impacts for more specific discussion"
}

# Process the agent decision
sync_bridge = AgentLLMSyncBridge(manager.get_orchestrator(session_id))
result = await sync_bridge.handle_agent_decision(agent_decision)

# System will:
# 1. Analyze semantic impact (moderate, requires local rewind)
# 2. Pause generation temporarily
# 3. Rewind to after "challenges"
# 4. Insert ", particularly in coastal regions,"
# 5. Resume generation with the modified context
# 6. Continue with "Coastal areas face rising sea levels..." (influenced by the edit)