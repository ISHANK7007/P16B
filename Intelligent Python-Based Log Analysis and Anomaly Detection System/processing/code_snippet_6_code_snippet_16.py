class TriggerDebouncer:
    """Debounce escalation trigger evaluations for high-volume alerts"""
    
    def __init__(self):
        self.last_evaluation: Dict[str, float] = {}  # fingerprint -> timestamp
        self.evaluation_counts: Dict[str, int] = {}  # fingerprint -> count in window
        self.suppressed_count: Dict[str, int] = {}  # fingerprint -> suppressed evaluations
        self.debounce_windows: Dict[str, float] = {}  # fingerprint -> window size (seconds)
    
    def should_evaluate(self, 
                       fingerprint: str, 
                       current_time: Optional[float] = None,
                       default_window: float = 60.0) -> bool:
        """
        Determine if an evaluation should proceed or be suppressed.
        Returns True if evaluation should proceed, False if it should be suppressed.
        """
        now = current_time or time.time()
        
        # Initialize counters for new fingerprints
        if fingerprint not in self.last_evaluation:
            self.last_evaluation[fingerprint] = now
            self.evaluation_counts[fingerprint] = 1
            self.suppressed_count[fingerprint] = 0
            self.debounce_windows[fingerprint] = default_window
            return True
            
        # Get the debounce window for this fingerprint
        window = self.debounce_windows[fingerprint]
        last_time = self.last_evaluation[fingerprint]
        
        # If we're outside the debounce window, allow evaluation
        if now - last_time > window:
            self.last_evaluation[fingerprint] = now
            self.evaluation_counts[fingerprint] += 1
            return True
            
        # We're inside the debounce window, suppress evaluation
        self.suppressed_count[fingerprint] += 1
        
        # Adaptive window: increase window size for frequently triggered alerts
        if self.suppressed_count[fingerprint] > 10:
            # Double the window size for highly active fingerprints
            self.debounce_windows[fingerprint] = min(window * 2, 3600)  # Max 1 hour
            
        return False
    
    def record_action_taken(self, fingerprint: str) -> None:
        """
        Record that an action was taken for this fingerprint.
        This resets the debounce window to prevent over-suppression.
        """
        now = time.time()
        self.last_evaluation[fingerprint] = now
        # Reset adaptive window after action is taken
        self.debounce_windows[fingerprint] = 60.0  # Reset to default
        self.suppressed_count[fingerprint] = 0
    
    def get_stats(self) -> Dict:
        """Get debouncer statistics"""
        return {
            "tracked_fingerprints": len(self.last_evaluation),
            "total_suppressed": sum(self.suppressed_count.values()),
            "average_window": sum(self.debounce_windows.values()) / max(len(self.debounce_windows), 1),
            "max_window": max(self.debounce_windows.values()) if self.debounce_windows else 0
        }