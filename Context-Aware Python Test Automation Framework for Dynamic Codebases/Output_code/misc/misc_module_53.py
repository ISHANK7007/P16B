class SwarmCoordinationManager:
    """
    Coordinates the work of many agents editing the same prompt
    with optimized arbitration
    """
    def __init__(self, partitioner=None, arbitration_engine=None, score_aggregator=None):
        self.partitioner = partitioner or ConflictPartitioner()
        self.arbitration_engine = arbitration_engine or ParallelArbitrationEngine()
        self.score_aggregator = score_aggregator or BatchScoreAggregator()
        self.agent_registry = {}  # Maps agent_id to Agent objects
        self.active_sessions = {}  # Maps session_id to active editing sessions
        
    def register_agent(self, agent):
        """Register an agent with the swarm"""
        self.agent_registry[agent.id] = agent
        
    def create_editing_session(self, prompt, context=None):
        """
        Create a new multi-agent editing session
        Returns a session ID
        """
        session_id = str(uuid.uuid4())
        
        self.active_sessions[session_id] = {
            "prompt": prompt,
            "context": context or {},
            "active_agents": set(),
            "proposals": [],
            "arbitration_state": "idle",
            "created": time.time(),
            "last_update": time.time()
        }
        
        return session_id
        
    def add_agent_to_session(self, session_id, agent_id):
        """Add an agent to an editing session"""
        if session_id not in self.active_sessions:
            return False
            
        if agent_id not in self.agent_registry:
            return False
            
        self.active_sessions[session_id]["active_agents"].add(agent_id)
        self.active_sessions[session_id]["last_update"] = time.time()
        
        return True
        
    def submit_proposal(self, session_id, agent_id, mutation_proposal):
        """
        Submit a mutation proposal to a session
        Returns acceptance status
        """
        if session_id not in self.active_sessions:
            return False
            
        session = self.active_sessions[session_id]
        
        if agent_id not in session["active_agents"]:
            return False
            
        # Add to proposals
        session["proposals"].append(mutation_proposal)
        session["last_update"] = time.time()
        
        # Check if we should trigger arbitration
        if self._should_trigger_arbitration(session):
            self._begin_arbitration(session_id)
            
        return True
        
    def get_arbitration_status(self, session_id):
        """Get the status of arbitration for a session"""
        if session_id not in self.active_sessions:
            return None
            
        session = self.active_sessions[session_id]
        
        if "arbitration_future" in session:
            completion = session["arbitration_future"].get_completion_percentage()
            return {
                "state": session["arbitration_state"],
                "completion": completion,
                "proposal_count": len(session["proposals"])
            }
            
        return {
            "state": session["arbitration_state"],
            "completion": 0.0,
            "proposal_count": len(session["proposals"])
        }
        
    def get_arbitration_results(self, session_id, wait=False, timeout=None):
        """
        Get arbitration results for a session
        If wait=True, blocks until results are available or timeout
        """
        if session_id not in self.active_sessions:
            return None
            
        session = self.active_sessions[session_id]
        
        if session["arbitration_state"] != "completed" and not wait:
            return None
            
        if "arbitration_future" in session:
            try:
                results = session["arbitration_future"].result(timeout)
                return results
            except TimeoutError:
                return None
                
        return None
        
    def apply_arbitration_results(self, session_id):
        """
        Apply the results of arbitration to the prompt
        Returns the updated prompt
        """
        if session_id not in self.active_sessions:
            return None
            
        session = self.active_sessions[session_id]
        
        if session["arbitration_state"] != "completed":
            return None
            
        results = self.get_arbitration_results(session_id)
        if not results:
            return session["prompt"]
            
        # Find winning proposal
        winning_id = max(results.keys(), key=lambda k: results[k])
        winning_proposal = None
        
        for proposal in session["proposals"]:
            if proposal.id == winning_id:
                winning_proposal = proposal
                break
                
        if not winning_proposal:
            return session["prompt"]
            
        # Apply the winning proposal
        updated_prompt = session["prompt"].apply_mutation(winning_proposal.mutation)
        session["prompt"] = updated_prompt
        
        # Clear proposals for next round
        session["proposals"] = []
        session["arbitration_state"] = "idle"
        if "arbitration_future" in session:
            del session["arbitration_future"]
            
        return updated_prompt
        
    def _should_trigger_arbitration(self, session):
        """Determine if arbitration should be triggered"""
        # Trigger if we have proposals from all active agents
        if len(session["proposals"]) >= len(session["active_agents"]):
            return True
            
        # Trigger if we have high-urgency proposals
        for proposal in session["proposals"]:
            if proposal.metadata.get("urgency", 0) > 0.8:
                return True
                
        # Trigger if we have at least 3 proposals and it's been more than 5 seconds
        if (len(session["proposals"]) >= 3 and 
                time.time() - session["last_arbitration_time"] > 5):
            return True
            
        return False
        
    def _begin_arbitration(self, session_id):
        """Begin the arbitration process for a session"""
        session = self.active_sessions[session_id]
        
        # Update state
        session["arbitration_state"] = "in_progress"
        session["last_arbitration_time"] = time.time()
        
        # Partition proposals into conflict regions
        conflict_regions = self.partitioner.partition_mutations(
            session["proposals"],
            session["context"]
        )
        
        # Start parallel arbitration
        future = self.arbitration_engine.process_regions(
            conflict_regions,
            session["context"],
            self.score_aggregator
        )
        
        # Store future for status checks
        session["arbitration_future"] = future
        
        # Add completion callback
        def on_complete():
            session["arbitration_state"] = "completed"
            
        future.add_done_callback(on_complete)