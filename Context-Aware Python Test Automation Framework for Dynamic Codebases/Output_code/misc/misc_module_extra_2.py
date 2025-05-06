class SimulationSnapshotPack:
    def __init__(self, snapshot_id, creation_timestamp):
        self.snapshot_id = snapshot_id
        self.creation_timestamp = creation_timestamp
        self.llm_contexts = {}  # Keyed by persona+format combo
        self.constraint_cache = {}  # Pre-compiled constraint evaluators
        self.tool_manifests = {}  # Shared tool definitions
        self.persona_fingerprints = {}  # Behavioral fingerprints
        
    def warm_start_simulation(self, format_types: List[PromptFormat], 
                             persona_types: List[PersonaType],
                             capabilities: List[ModelCapability]) -> 'SimulationEnvironment':
        """Initialize a simulation environment with pre-warmed components"""
        # Select only required components for minimal loading
        relevant_llm_contexts = self._filter_relevant_contexts(format_types, persona_types)
        relevant_constraints = self._filter_relevant_constraints(format_types)
        
        # Create simulation with pre-loaded components
        return SimulationEnvironment(
            contexts=relevant_llm_contexts,
            constraints=relevant_constraints,
            tool_manifests=self.tool_manifests,
            persona_fingerprints=self._filter_personas(persona_types)
        )
        
    def _filter_relevant_contexts(self, formats, personas):
        """Select only needed LLM contexts based on format and persona combinations"""
        keys = [(f, p) for f in formats for p in personas]
        return {k: self.llm_contexts[k] for k in keys if k in self.llm_contexts}

class SnapshotManager:
    """Manages creation and retrieval of simulation snapshots"""
    
    def __init__(self, snapshot_dir, max_snapshots=10, ttl_hours=24):
        self.snapshot_dir = snapshot_dir
        self.max_snapshots = max_snapshots
        self.ttl_hours = ttl_hours
        self.snapshot_index = self._load_snapshot_index()
        
    def get_snapshot(self, req_formats, req_personas, req_capabilities):
        """Retrieve the most applicable snapshot for the given requirements"""
        # Find best matching snapshot using similarity scoring
        best_match = self._find_best_match(req_formats, req_personas, req_capabilities)
        if best_match and self._is_fresh(best_match):
            return self._load_snapshot(best_match)
        
        # No suitable snapshot found, create new one
        return self._create_new_snapshot(req_formats, req_personas, req_capabilities)
    
    def _find_best_match(self, formats, personas, capabilities):
        """Find the best matching snapshot using a similarity score"""
        if not self.snapshot_index:
            return None
            
        scores = []
        for snapshot_id, metadata in self.snapshot_index.items():
            # Calculate format, persona and capability coverage
            format_coverage = len(set(formats) & set(metadata['formats'])) / len(formats)
            persona_coverage = len(set(personas) & set(metadata['personas'])) / len(personas)
            capability_coverage = len(set(capabilities) & set(metadata['capabilities'])) / len(capabilities)
            
            # Weight the scores - prioritize persona matches
            weighted_score = (format_coverage * 0.3 + 
                             persona_coverage * 0.5 + 
                             capability_coverage * 0.2)
            
            scores.append((snapshot_id, weighted_score))
        
        # Return highest scoring snapshot above threshold
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[0][0] if scores and scores[0][1] >= 0.8 else None

class SimulationCoordinator:
    """Coordinates CI simulation runs with optimized startup"""
    
    def __init__(self, snapshot_manager):
        self.snapshot_manager = snapshot_manager
        self.active_simulations = {}
        self.warm_cache = {}  # Format+Persona keyed warm cache
        
    async def start_simulation(self, test_config):
        """Start a simulation with minimal warm-start latency"""
        # Extract requirements
        formats = test_config.get('formats', [PromptFormat.RAW_TEXT])
        personas = test_config.get('personas', [PersonaType.GENERALIST])
        capabilities = test_config.get('capabilities', [ModelCapability.BASIC])
        
        # Get appropriate snapshot
        snapshot = self.snapshot_manager.get_snapshot(formats, personas, capabilities)
        
        # Create environment with pre-warmed components
        env = snapshot.warm_start_simulation(formats, personas, capabilities)
        
        # Keep track of this simulation
        sim_id = f"sim-{uuid.uuid4()}"
        self.active_simulations[sim_id] = env
        
        return sim_id, env