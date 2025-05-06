from typing import Dict, List, Any, Optional, Tuple, Set, Union, Callable, TypeVar
from dataclasses import dataclass, field
from enum import Enum, auto
import numpy as np
import asyncio
import json
import hashlib
import datetime
import scipy.stats
from sklearn.metrics.pairwise import cosine_similarity
from collections import Counter, defaultdict
import matplotlib.pyplot as plt
from io import BytesIO
import base64

class DivergenceMetricType(Enum):
    """Types of divergence metrics"""
    ENTROPY = auto()           # Information-theoretic entropy of mutation decisions
    VECTOR_DISTANCE = auto()   # Distance between explanation vectors
    DECISION_AGREEMENT = auto() # Agreement rate among personas
    SUCCESS_RATE = auto()      # Success rate variation across personas
    CONSTRAINT_VIOLATION = auto() # Different constraint violations observed
    SEMANTIC_DRIFT = auto()    # Semantic drift from original prompt

@dataclass
class PersonaDecision:
    """Represents a decision made by a persona during mutation simulation"""
    persona_id: str
    persona_type: PersonaType
    mutation_id: str
    original_prompt: str
    mutated_prompt: str
    confidence: float
    explanation: str
    rationale_vector: Optional[List[float]] = None  # Embedding of explanation
    constraint_scores: Dict[str, float] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def generate_decision_hash(self) -> str:
        """Generate a hash representing the core decision"""
        decision_text = f"{self.mutated_prompt}:{self.confidence}"
        return hashlib.sha256(decision_text.encode()).hexdigest()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "persona_id": self.persona_id,
            "persona_type": self.persona_type.name,
            "mutation_id": self.mutation_id,
            "confidence": self.confidence,
            "explanation": self.explanation,
            "constraint_scores": self.constraint_scores,
            "tags": self.tags,
            "original_prompt": self.original_prompt,
            "mutated_prompt": self.mutated_prompt,
            # Don't include the full vector in JSON for efficiency
            "vector_present": self.rationale_vector is not None
        }

@dataclass
class DivergenceMetric:
    """A calculated divergence metric"""
    type: DivergenceMetricType
    value: float
    component_values: Dict[str, float] = field(default_factory=dict)
    explanation: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "type": self.type.name,
            "value": self.value,
            "component_values": self.component_values,
            "explanation": self.explanation
        }

@dataclass
class PersonaDivergenceAnalysis:
    """Analysis of divergence between multiple persona decisions"""
    mutation_id: str
    decisions: List[PersonaDecision]
    metrics: Dict[DivergenceMetricType, DivergenceMetric] = field(default_factory=dict)
    decision_clusters: List[List[str]] = field(default_factory=list)  # Clusters of persona IDs
    entropy: float = 0.0
    agreement_rate: float = 0.0
    max_vector_distance: float = 0.0
    timestamp: datetime.datetime = field(default_factory=datetime.datetime.now)
    
    def calculate_all_metrics(self) -> Dict[DivergenceMetricType, DivergenceMetric]:
        """Calculate all divergence metrics"""
        self.metrics[DivergenceMetricType.ENTROPY] = self.calculate_entropy_metric()
        self.metrics[DivergenceMetricType.DECISION_AGREEMENT] = self.calculate_agreement_metric()
        self.metrics[DivergenceMetricType.VECTOR_DISTANCE] = self.calculate_vector_distance_metric()
        self.metrics[DivergenceMetricType.CONSTRAINT_VIOLATION] = self.calculate_constraint_violation_metric()
        self.entropy = self.metrics[DivergenceMetricType.ENTROPY].value
        self.agreement_rate = self.metrics[DivergenceMetricType.DECISION_AGREEMENT].value
        
        return self.metrics
    
    def calculate_entropy_metric(self) -> DivergenceMetric:
        """Calculate entropy-based divergence metric"""
        # Group decisions by their core decision hash
        decision_hashes = [d.generate_decision_hash() for d in self.decisions]
        counts = Counter(decision_hashes)
        
        # Calculate probabilities
        total = len(decision_hashes)
        probabilities = [count/total for count in counts.values()]
        
        # Calculate entropy using scipy
        entropy = scipy.stats.entropy(probabilities, base=2)
        
        # Max possible entropy for this number of decisions
        max_entropy = np.log2(min(len(self.decisions), len(counts)))
        normalized_entropy = entropy / max_entropy if max_entropy > 0 else 0
        
        # Track individual contribution to entropy
        persona_contributions = {}
        for i, decision in enumerate(self.decisions):
            hash_key = decision_hashes[i]
            probability = counts[hash_key] / total
            information_content = -np.log2(probability)
            persona_contributions[decision.persona_id] = information_content
        
        return DivergenceMetric(
            type=DivergenceMetricType.ENTROPY,
            value=normalized_entropy,
            component_values=persona_contributions,
            explanation=f"Normalized entropy: {normalized_entropy:.3f} of maximum {max_entropy:.3f} bits. "
                       f"Higher value indicates more diverse decisions."
        )
    
    def calculate_agreement_metric(self) -> DivergenceMetric:
        """Calculate agreement-based divergence metric"""
        # Count occurrences of each unique decision
        decision_hashes = [d.generate_decision_hash() for d in self.decisions]
        counts = Counter(decision_hashes)
        
        # Find the most common decision
        most_common_hash, most_common_count = counts.most_common(1)[0]
        
        # Calculate agreement rate
        agreement_rate = most_common_count / len(self.decisions)
        
        # Identify which personas agreed on the most common decision
        agreed_personas = [
            d.persona_id for i, d in enumerate(self.decisions) 
            if decision_hashes[i] == most_common_hash
        ]
        
        # Map all personas to their agreement group (1 for majority, 0 for others)
        persona_agreement = {
            d.persona_id: 1.0 if d.generate_decision_hash() == most_common_hash else 0.0
            for d in self.decisions
        }
        
        # Store the clusters for later use
        self.decision_clusters = []
        for hash_key, _ in counts.most_common():
            cluster = [
                d.persona_id for i, d in enumerate(self.decisions)
                if decision_hashes[i] == hash_key
            ]
            self.decision_clusters.append(cluster)
        
        return DivergenceMetric(
            type=DivergenceMetricType.DECISION_AGREEMENT,
            value=agreement_rate,
            component_values=persona_agreement,
            explanation=f"Agreement rate: {agreement_rate:.2f}. "
                       f"{most_common_count} of {len(self.decisions)} personas agreed on the same decision."
        )
    
    def calculate_vector_distance_metric(self) -> DivergenceMetric:
        """Calculate vector distance-based divergence metric"""
        # Filter decisions with vectors
        decisions_with_vectors = [d for d in self.decisions if d.rationale_vector is not None]
        
        if len(decisions_with_vectors) < 2:
            return DivergenceMetric(
                type=DivergenceMetricType.VECTOR_DISTANCE,
                value=0.0,
                explanation="Insufficient vector data for distance calculation."
            )
        
        # Calculate pairwise distances
        vectors = np.array([d.rationale_vector for d in decisions_with_vectors])
        similarities = cosine_similarity(vectors)
        
        # Convert similarities to distances (1 - similarity)
        distances = 1 - similarities
        
        # Calculate maximum and average distances
        max_distance = np.max(distances)
        avg_distance = np.mean(distances)
        
        # Calculate distances between each persona and the centroid
        centroid = np.mean(vectors, axis=0)
        centroid_distances = {
            d.persona_id: 1 - cosine_similarity(
                np.array([d.rationale_vector]), np.array([centroid])
            )[0][0]
            for d in decisions_with_vectors
        }
        
        return DivergenceMetric(
            type=DivergenceMetricType.VECTOR_DISTANCE,
            value=max_distance,  # Use max distance as the primary metric
            component_values=centroid_distances,
            explanation=f"Maximum vector distance: {max_distance:.3f}, Average: {avg_distance:.3f}. "
                       f"Higher values indicate more diverse explanations."
        )
    
    def calculate_constraint_violation_metric(self) -> DivergenceMetric:
        """Calculate constraint violation divergence metric"""
        # Collect all constraint keys
        all_constraints = set()
        for decision in self.decisions:
            all_constraints.update(decision.constraint_scores.keys())
        
        if not all_constraints:
            return DivergenceMetric(
                type=DivergenceMetricType.CONSTRAINT_VIOLATION,
                value=0.0,
                explanation="No constraint data available."
            )
        
        # For each constraint, calculate variance in scores
        constraint_variances = {}
        for constraint in all_constraints:
            scores = [
                d.constraint_scores.get(constraint, 0.0) 
                for d in self.decisions 
                if constraint in d.constraint_scores
            ]
            
            if scores:
                constraint_variances[constraint] = np.var(scores)
        
        # Average variance across all constraints
        avg_variance = np.mean(list(constraint_variances.values())) if constraint_variances else 0.0
        
        # Identify constraints with highest variance
        sorted_constraints = sorted(
            constraint_variances.items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        
        high_variance_constraints = sorted_constraints[:3] if sorted_constraints else []
        
        explanation_parts = [f"Average constraint score variance: {avg_variance:.3f}."]
        if high_variance_constraints:
            explanation_parts.append("Highest variance constraints:")
            for constraint, variance in high_variance_constraints:
                explanation_parts.append(f"- {constraint}: {variance:.3f}")
        
        return DivergenceMetric(
            type=DivergenceMetricType.CONSTRAINT_VIOLATION,
            value=avg_variance,
            component_values={c: v for c, v in constraint_variances.items()},
            explanation=" ".join(explanation_parts)
        )
    
    def generate_visual_analysis(self) -> Optional[str]:
        """Generate a visual representation of the divergence analysis"""
        try:
            # Create a figure with multiple subplots
            fig, axes = plt.subplots(2, 2, figsize=(12, 10))
            fig.suptitle(f"Persona Divergence Analysis for Mutation {self.mutation_id}", fontsize=16)
            
            # Plot 1: Entropy by persona
            if DivergenceMetricType.ENTROPY in self.metrics:
                metric = self.metrics[DivergenceMetricType.ENTROPY]
                personas = list(metric.component_values.keys())
                values = list(metric.component_values.values())
                
                axes[0, 0].bar(range(len(personas)), values, tick_label=personas)
                axes[0, 0].set_title(f"Information Content by Persona (Entropy: {metric.value:.3f})")
                axes[0, 0].set_ylabel("Information Content (bits)")
                axes[0, 0].tick_params(axis='x', rotation=45)
            
            # Plot 2: Agreement clusters
            if self.decision_clusters:
                cluster_sizes = [len(cluster) for cluster in self.decision_clusters]
                labels = [f"Cluster {i+1}" for i in range(len(cluster_sizes))]
                
                axes[0, 1].pie(cluster_sizes, labels=labels, autopct='%1.1f%%')
                axes[0, 1].set_title("Decision Clusters")
            
            # Plot 3: Vector distances to centroid
            if DivergenceMetricType.VECTOR_DISTANCE in self.metrics:
                metric = self.metrics[DivergenceMetricType.VECTOR_DISTANCE]
                if metric.component_values:
                    personas = list(metric.component_values.keys())
                    distances = list(metric.component_values.values())
                    
                    axes[1, 0].bar(range(len(personas)), distances, tick_label=personas)
                    axes[1, 0].set_title(f"Distance to Centroid (Max Distance: {metric.value:.3f})")
                    axes[1, 0].set_ylabel("Cosine Distance")
                    axes[1, 0].tick_params(axis='x', rotation=45)
            
            # Plot 4: Constraint violation variance
            if DivergenceMetricType.CONSTRAINT_VIOLATION in self.metrics:
                metric = self.metrics[DivergenceMetricType.CONSTRAINT_VIOLATION]
                if metric.component_values:
                    constraints = list(metric.component_values.keys())
                    variances = list(metric.component_values.values())
                    
                    # Sort by variance
                    sorted_indices = np.argsort(variances)[::-1]
                    constraints = [constraints[i] for i in sorted_indices]
                    variances = [variances[i] for i in sorted_indices]
                    
                    # Take top 5 for clarity
                    constraints = constraints[:5]
                    variances = variances[:5]
                    
                    axes[1, 1].bar(range(len(constraints)), variances, tick_label=constraints)
                    axes[1, 1].set_title(f"Constraint Score Variance (Avg: {metric.value:.3f})")
                    axes[1, 1].set_ylabel("Variance")
                    axes[1, 1].tick_params(axis='x', rotation=45)
            
            plt.tight_layout()
            
            # Convert plot to base64 string
            buffer = BytesIO()
            plt.savefig(buffer, format='png')
            plt.close(fig)
            buffer.seek(0)
            image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
            return image_base64
            
        except Exception as e:
            print(f"Error generating visual analysis: {e}")
            return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "mutation_id": self.mutation_id,
            "timestamp": self.timestamp.isoformat(),
            "entropy": self.entropy,
            "agreement_rate": self.agreement_rate,
            "max_vector_distance": self.max_vector_distance,
            "decision_clusters": self.decision_clusters,
            "metrics": {k.name: v.to_dict() for k, v in self.metrics.items()},
            "decision_count": len(self.decisions)
            # Don't include full decisions in the summary for efficiency
        }
    
    def detailed_report(self) -> Dict[str, Any]:
        """Generate a detailed report with all data"""
        report = self.to_dict()
        report["decisions"] = [d.to_dict() for d in self.decisions]
        report["visualization"] = self.generate_visual_analysis()
        
        # Add decision clusters with their members
        cluster_details = []
        for i, cluster in enumerate(self.decision_clusters):
            # Find a representative decision from this cluster
            rep_persona_id = cluster[0] if cluster else None
            rep_decision = next((d for d in self.decisions if d.persona_id == rep_persona_id), None)
            
            if rep_decision:
                cluster_details.append({
                    "cluster_id": i + 1,
                    "size": len(cluster),
                    "members": cluster,
                    "representative_prompt": rep_decision.mutated_prompt,
                    "confidence": rep_decision.confidence
                })
        
        report["cluster_details"] = cluster_details
        return report

class DivergenceAnalysisService:
    """Service for analyzing persona divergence in mutation simulations"""
    
    def __init__(self, vector_embedding_service: Optional[Any] = None):
        self.analysis_cache: Dict[str, PersonaDivergenceAnalysis] = {}
        self.vector_service = vector_embedding_service
    
    async def analyze_persona_decisions(self, 
                                    mutation_id: str,
                                    decisions: List[PersonaDecision]) -> PersonaDivergenceAnalysis:
        """Analyze decisions from multiple personas for a single mutation"""
        # Generate vectors for explanations if not already present
        decisions_with_vectors = await self._ensure_vectors(decisions)
        
        # Create analysis object
        analysis = PersonaDivergenceAnalysis(
            mutation_id=mutation_id,
            decisions=decisions_with_vectors
        )
        
        # Calculate all metrics
        analysis.calculate_all_metrics()
        
        # Cache the analysis
        self.analysis_cache[mutation_id] = analysis
        
        return analysis
    
    async def _ensure_vectors(self, decisions: List[PersonaDecision]) -> List[PersonaDecision]:
        """Ensure all decisions have rationale vectors"""
        if not self.vector_service:
            return decisions
        
        decisions_to_vectorize = [d for d in decisions if d.rationale_vector is None]
        
        if not decisions_to_vectorize:
            return decisions
        
        # Generate vectors in batches
        texts = [f"{d.mutated_prompt}\n\nRationale: {d.explanation}" for d in decisions_to_vectorize]
        vectors = await self.vector_service.embed_batch(texts)
        
        # Update decisions with vectors
        for decision, vector in zip(decisions_to_vectorize, vectors):
            decision.rationale_vector = vector
        
        return decisions
    
    async def get_cached_analysis(self, mutation_id: str) -> Optional[PersonaDivergenceAnalysis]:
        """Get cached analysis if available"""
        return self.analysis_cache.get(mutation_id)
    
    async def compare_divergence_across_mutations(self, 
                                               mutation_ids: List[str]) -> Dict[str, Any]:
        """Compare divergence across multiple mutations"""
        analyses = []
        
        for mutation_id in mutation_ids:
            analysis = self.analysis_cache.get(mutation_id)
            if analysis:
                analyses.append(analysis)
        
        if not analyses:
            return {"error": "No analyses found for the requested mutations"}
        
        # Collect metrics across mutations
        metrics_by_type = defaultdict(list)
        
        for analysis in analyses:
            for metric_type, metric in analysis.metrics.items():
                metrics_by_type[metric_type].append((analysis.mutation_id, metric.value))
        
        # Generate comparison report
        comparison = {
            "mutation_count": len(analyses),
            "metrics_summary": {}
        }
        
        for metric_type, values in metrics_by_type.items():
            mutation_ids, metric_values = zip(*values)
            
            comparison["metrics_summary"][metric_type.name] = {
                "average": np.mean(metric_values),
                "min": np.min(metric_values),
                "max": np.max(metric_values),
                "std_dev": np.std(metric_values),
                "highest_mutation": mutation_ids[np.argmax(metric_values)],
                "lowest_mutation": mutation_ids[np.argmin(metric_values)]
            }
        
        # Generate top-level summary
        if DivergenceMetricType.ENTROPY in metrics_by_type:
            _, entropy_values = zip(*metrics_by_type[DivergenceMetricType.ENTROPY])
            comparison["average_entropy"] = np.mean(entropy_values)
        
        if DivergenceMetricType.DECISION_AGREEMENT in metrics_by_type:
            _, agreement_values = zip(*metrics_by_type[DivergenceMetricType.DECISION_AGREEMENT])
            comparison["average_agreement"] = np.mean(agreement_values)
        
        return comparison

class PersonaReplaySimulator:
    """Simulates mutations with multiple personas and analyzes divergence"""
    
    def __init__(self, 
                replay_engine: MutationReplayEngine,
                personas: Dict[str, Persona],
                divergence_service: DivergenceAnalysisService,
                vector_service: Optional[Any] = None):
        self.replay_engine = replay_engine
        self.personas = personas
        self.divergence_service = divergence_service
        self.vector_service = vector_service
        self.simulation_results: Dict[str, Dict[str, Any]] = {}
    
    async def simulate_with_personas(self, 
                                  mutation_trace: MutationTrace,
                                  persona_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """Simulate a mutation with multiple personas and analyze divergence"""
        # Determine which personas to use
        if persona_ids is None:
            persona_ids = list(self.personas.keys())
        
        selected_personas = [self.personas[pid] for pid in persona_ids if pid in self.personas]
        
        if not selected_personas:
            return {"error": "No valid personas specified"}
        
        # Simulate with each persona
        persona_decisions = []
        simulation_tasks = []
        
        for persona in selected_personas:
            # Create a specialized context for this persona
            persona_context = ExecutionContext(
                model_version=mutation_trace.model_version,
                random_seed=hash(persona.name) % 10000,  # Deterministic but persona-specific seed
                constraint_set=[],  # Will be populated from the trace
                parameters={"persona": persona.to_dict()}
            )
            
            # Add the simulation task
            task = self.replay_engine.replay_trace_with_persona(
                trace_id=mutation_trace.mutation_id,
                persona=persona,
                context=persona_context
            )
            simulation_tasks.append((persona, task))
        
        # Wait for all simulations to complete
        for persona, task in simulation_tasks:
            try:
                result = await task
                
                # Extract constraint scores from validation results
                constraint_scores = {}
                if result.validation_results and "constraint_details" in result.validation_results:
                    for constraint, passed in result.validation_results["constraint_details"].items():
                        constraint_scores[constraint] = 1.0 if passed else 0.0
                
                # Determine confidence based on success and validation
                confidence = 0.9 if result.success else 0.3
                if result.validation_results:
                    # Adjust confidence based on validation results
                    validation_score = sum(constraint_scores.values()) / max(1, len(constraint_scores))
                    confidence *= (0.5 + 0.5 * validation_score)  # Scale confidence by validation
                
                # Create a decision object
                decision = PersonaDecision(
                    persona_id=persona.name,
                    persona_type=persona.type,
                    mutation_id=mutation_trace.mutation_id,
                    original_prompt=mutation_trace.original_prompt,
                    mutated_prompt=result.replay_output or mutation_trace.mutated_prompt,
                    confidence=confidence,
                    explanation=result.llm_response.get("explanation", "No explanation provided"),
                    constraint_scores=constraint_scores,
                    tags=["replay_simulation"],
                    metadata={
                        "success": result.success,
                        "execution_metrics": result.execution_metrics
                    }
                )
                
                persona_decisions.append(decision)
                
            except Exception as e:
                print(f"Error simulating with persona {persona.name}: {e}")
        
        if not persona_decisions:
            return {"error": "All persona simulations failed"}
        
        # Analyze the divergence
        analysis = await self.divergence_service.analyze_persona_decisions(
            mutation_id=mutation_trace.mutation_id,
            decisions=persona_decisions
        )
        
        # Create simulation result
        simulation_result = {
            "mutation_id": mutation_trace.mutation_id,
            "persona_count": len(persona_decisions),
            "decisions": [d.to_dict() for d in persona_decisions],
            "divergence_analysis": analysis.to_dict(),
            "summary": {
                "entropy": analysis.entropy,
                "agreement_rate": analysis.agreement_rate,
                "variant_count": len(analysis.decision_clusters)
            }
        }
        
        # Store result
        self.simulation_results[mutation_trace.mutation_id] = simulation_result
        
        return simulation_result
    
    async def batch_simulate_mutations(self, 
                                   mutation_ids: List[str], 
                                   persona_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """Batch simulate multiple mutations with personas"""
        results = {}
        
        for mutation_id in mutation_ids:
            try:
                # Retrieve the mutation trace
                trace = self.replay_engine.trace_repository.get(mutation_id)
                if not trace:
                    results[mutation_id] = {"error": f"Trace {mutation_id} not found"}
                    continue
                
                # Simulate with personas
                result = await self.simulate_with_personas(trace, persona_ids)
                results[mutation_id] = result
                
            except Exception as e:
                results[mutation_id] = {"error": f"Simulation error: {str(e)}"}
        
        # Compile aggregate statistics
        successful_simulations = [mid for mid, result in results.items() if "error" not in result]
        
        if successful_simulations:
            # Compare divergence across mutations
            comparison = await self.divergence_service.compare_divergence_across_mutations(
                successful_simulations
            )
            
            # Add the comparison to the result
            results["_comparison"] = comparison
        
        return results
    
    async def generate_divergence_report(self, 
                                      mutation_id: str,
                                      include_visualization: bool = True) -> Dict[str, Any]:
        """Generate a detailed divergence report for a mutation"""
        # Get the cached analysis or re-analyze
        analysis = await self.divergence_service.get_cached_analysis(mutation_id)
        
        if not analysis:
            if mutation_id not in self.simulation_results:
                return {"error": f"No simulation results found for mutation {mutation_id}"}
            
            # Recreate the analysis from stored decisions
            simulation_result = self.simulation_results[mutation_id]
            decision_dicts = simulation_result.get("decisions", [])
            
            # Convert back to PersonaDecision objects
            decisions = []
            for d_dict in decision_dicts:
                decision = PersonaDecision(
                    persona_id=d_dict["persona_id"],
                    persona_type=PersonaType[d_dict["persona_type"]],
                    mutation_id=d_dict["mutation_id"],
                    original_prompt=d_dict["original_prompt"],
                    mutated_prompt=d_dict["mutated_prompt"],
                    confidence=d_dict["confidence"],
                    explanation=d_dict["explanation"],
                    constraint_scores=d_dict.get("constraint_scores", {}),
                    tags=d_dict.get("tags", [])
                )
                decisions.append(decision)
            
            # Analyze the decisions
            if decisions:
                analysis = await self.divergence_service.analyze_persona_decisions(
                    mutation_id=mutation_id,
                    decisions=decisions
                )
            else:
                return {"error": "No decision data available for analysis"}
        
        # Generate the detailed report
        report = analysis.detailed_report()
        
        # Add visualization if requested
        if include_visualization and "visualization" not in report:
            report["visualization"] = analysis.generate_visual_analysis()
        
        return report