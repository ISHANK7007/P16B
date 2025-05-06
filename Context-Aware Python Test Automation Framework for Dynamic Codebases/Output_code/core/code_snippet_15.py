class DualStateBuffer:
    """Maintains synchronized prompt and generation buffers"""
    def __init__(self):
        self.prompt_buffer = []
        self.generation_buffer = []
        self.sync_points = []  # Points where the buffers are known to align
        
    def record_sync_point(self, prompt_idx, gen_idx, confidence=1.0):
        """Record a point where prompt and generation buffers align"""
        self.sync_points.append({
            "prompt_idx": prompt_idx,
            "gen_idx": gen_idx,
            "confidence": confidence
        })