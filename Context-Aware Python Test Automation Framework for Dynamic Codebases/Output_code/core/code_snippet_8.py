class StreamingPromptCursor:
    """
    Manages bidirectional synchronization between agent edits and LLM token streams
    with semantic alignment windows, rewind capabilities, and rollback protection.
    """
    def __init__(self, initial_prompt, semantic_window_size=5):
        self.current_position = 0
        self.prompt_state = PromptState(initial_prompt)
        self.token_history = []
        self.semantic_window_size = semantic_window_size
        self.alignment_markers = {}  # Maps semantic concepts to token positions
        self.rewind_checkpoints = []  # Points where safe rewinding is possible
        self.rollback_guards = []     # Protections against unsafe rollbacks