class CausalityTracker:
    """Tracks causal influences between prompt and generated content"""
    def __init__(self):
        self.influence_graph = {}  # Maps prompt segments to influenced generations
        
    def record_influence(self, prompt_segment, generated_segment, strength):
        """Record that a prompt segment influenced a generated segment"""
        if prompt_segment not in self.influence_graph:
            self.influence_graph[prompt_segment] = []
            
        self.influence_graph[prompt_segment].append({
            "generated": generated_segment,
            "strength": strength
        })