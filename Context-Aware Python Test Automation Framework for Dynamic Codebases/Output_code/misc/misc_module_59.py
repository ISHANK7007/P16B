class SessionContext:
    """
    Maintains information about the session context for a mutation,
    supporting cross-session tracking and decay calculations.
    """
    def __init__(self):
        self.session_id = None  # Current session ID
        self.parent_session_ids = []  # Chain of parent sessions
        self.session_depth = 0  # How deep in the session chain
        self.hop_timestamps = []  # When each session hop occurred
        self.local_feedback_scores = {}  # Feedback within this session
        self.session_metadata = {}  # Additional session information
        
    def initialize_session(self, session_id, metadata=None):
        """Initialize for a new session"""
        self.session_id = session_id
        self.session_depth = 0
        self.session_metadata = metadata or {}
        self.hop_timestamps = [time.time()]
        
    def hop_to_new_session(self, new_session_id, metadata=None):
        """Record a hop to a new session"""
        if self.session_id:
            self.parent_session_ids.append(self.session_id)
        
        self.session_id = new_session_id
        self.session_depth += 1
        self.hop_timestamps.append(time.time())
        
        if metadata:
            self.session_metadata.update(metadata)
            
    def record_feedback(self, feedback_type, score, source=None):
        """Record session-local feedback"""
        if feedback_type not in self.local_feedback_scores:
            self.local_feedback_scores[feedback_type] = []
            
        self.local_feedback_scores[feedback_type].append({
            "score": score,
            "timestamp": time.time(),
            "source": source
        })
        
    def get_session_chain(self):
        """Get the full session lineage"""
        chain = self.parent_session_ids.copy()
        if self.session_id:
            chain.append(self.session_id)
        return chain
        
    def to_dict(self):
        """Convert to dictionary for serialization"""
        return {
            "session_id": self.session_id,
            "parent_sessions": self.parent_session_ids,
            "session_depth": self.session_depth,
            "hop_timestamps": self.hop_timestamps,
            "local_feedback": self.local_feedback_scores,
            "metadata": self.session_metadata
        }