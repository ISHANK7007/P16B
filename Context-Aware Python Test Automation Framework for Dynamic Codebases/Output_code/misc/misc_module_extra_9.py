class ComponentVersionRegistry:
    """Central registry for versioned components with compatibility checking"""
    
    def __init__(self):
        self.components = {}  # type_id -> {version -> instance}
        self.active_versions = {}  # type_id -> active_version
        self.deployment_status = {}  # version -> status
        
    def register_component(self, component_type, version, instance, compatibility=None):
        """Register a component version"""
        if component_type not in self.components:
            self.components[component_type] = {}
        
        self.components[component_type][version] = {
            'instance': instance,
            'compatibility': compatibility or {},
            'health': 1.0,
            'traffic_allocation': 0.0  # Start at 0%
        }
        
    def activate_version(self, component_type, version, traffic_percent=100):
        """Activate a specific version with traffic allocation"""
        if traffic_percent == 100:
            # Set as the primary active version
            self.active_versions[component_type] = version
        else:
            # For canary deployments, adjust traffic allocation
            for v in self.components[component_type]:
                # Reset other versions' allocation proportionally
                if v != version and v != self.active_versions.get(component_type):
                    self.components[component_type][v]['traffic_allocation'] = max(
                        0, (100 - traffic_percent) * 
                        self.components[component_type][v]['traffic_allocation'] / 100
                    )
            
            # Set new version allocation
            self.components[component_type][version]['traffic_allocation'] = traffic_percent
            
    def get_component(self, component_type, preferred_version=None, context=None):
        """Get component instance with dynamic routing logic"""
        if component_type not in self.components:
            raise KeyError(f"No components registered for {component_type}")
            
        # Explicit version request (for testing/debug)
        if preferred_version and preferred_version in self.components[component_type]:
            return self.components[component_type][preferred_version]['instance']
            
        # Traffic splitting for canary deployment
        active_version = self.active_versions.get(component_type)
        if active_version:
            # Check if we should route to canary based on allocation
            versions = list(self.components[component_type].keys())
            weights = [self.components[component_type][v]['traffic_allocation'] for v in versions]
            
            # Context-aware routing (e.g., route format-specific requests)
            if context and 'format' in context:
                format_type = context['format']
                if format_type in [PromptFormat.JSON, PromptFormat.SQL]:
                    # Specialized routing for structured formats
                    for v in versions:
                        comp_data = self.components[component_type][v]
                        if (comp_data.get('compatibility', {}).get('formats', []) and 
                            format_type in comp_data['compatibility']['formats']):
                            # Prefer versions with explicit format support
                            weights[versions.index(v)] *= 1.5
            
            # Select version based on weights
            selected_version = random.choices(versions, weights=weights)[0]
            return self.components[component_type][selected_version]['instance']
            
        # Fallback to latest registered version
        latest_version = max(self.components[component_type].keys())
        return self.components[component_type][latest_version]['instance']


class ShadowModeEvaluator:
    """Evaluates new components in shadow mode against current production versions"""
    
    def __init__(self, registry, anomaly_detector):
        self.registry = registry
        self.anomaly_detector = anomaly_detector
        self.shadow_results = {}  # Request ID -> {version -> result}
        
    async def evaluate_in_shadow(self, component_type, request_id, input_data, context=None):
        """Run a request through both current and shadow versions"""
        active_version = self.registry.active_versions.get(component_type)
        if not active_version:
            return None
            
        # Get all versions with non-zero traffic allocation for shadowing
        shadow_versions = [
            v for v, data in self.registry.components[component_type].items()
            if data['traffic_allocation'] > 0 and v != active_version
        ]
        
        if not shadow_versions:
            return None
            
        # Run active version (considered ground truth)
        active_component = self.registry.components[component_type][active_version]['instance']
        active_result = await self._run_component(active_component, input_data, context)
        
        # Run shadow versions in parallel
        shadow_results = {}
        for version in shadow_versions:
            shadow_component = self.registry.components[component_type][version]['instance']
            shadow_result = await self._run_component(shadow_component, input_data, context)
            shadow_results[version] = shadow_result
            
            # Compare results and detect anomalies
            comparison = self._compare_results(active_result, shadow_result, context)
            self.anomaly_detector.record_comparison(
                component_type, active_version, version, comparison, context
            )
            
        # Store all results for analysis
        self.shadow_results[request_id] = {
            'active': {active_version: active_result},
            'shadow': shadow_results
        }
        
        # Only return the active result (shadow mode doesn't affect output)
        return active_result
        
    async def _run_component(self, component, input_data, context):
        """Execute a component with the given input"""
        # Implementation depends on component type
        if hasattr(component, 'mutate'):
            return await component.mutate(input_data, context.get('format'))
        elif hasattr(component, 'validate'):
            return component.validate(input_data, context.get('format'))
        # Add more component types as needed
        
    def _compare_results(self, active_result, shadow_result, context):
        """Compare active and shadow results to detect meaningful differences"""
        # Simple implementation for demonstration
        if isinstance(active_result, PromptMutation) and isinstance(shadow_result, PromptMutation):
            return {
                'mutated_text_diff': self._text_difference(active_result.mutated, shadow_result.mutated),
                'rationale_diff': self._text_difference(active_result.mutation_rationale, 
                                                      shadow_result.mutation_rationale),
                'constraint_diff': self._constraint_difference(active_result.applied_constraints,
                                                             shadow_result.applied_constraints)
            }
        return {'difference_detected': active_result != shadow_result}


class DeploymentManager:
    """Manages the full deployment lifecycle"""
    
    def __init__(self, registry, evaluator, anomaly_detector):
        self.registry = registry
        self.evaluator = evaluator
        self.anomaly_detector = anomaly_detector
        self.deployment_states = {}  # deployment_id -> state
        self.rollback_checkpoints = {}  # deployment_id -> checkpoints
        
    async def start_deployment(self, component_type, new_version, instance, config):
        """Begin a new deployment with the specified strategy"""
        deployment_id = f"{component_type}-{new_version}-{uuid.uuid4()}"
        
        # Register the new component version
        self.registry.register_component(component_type, new_version, instance, 
                                        config.get('compatibility'))
        
        # Create deployment state
        self.deployment_states[deployment_id] = {
            'status': 'initializing',
            'component_type': component_type,
            'version': new_version,
            'start_time': datetime.datetime.now(),
            'current_phase': 'shadow',
            'traffic_allocation': 0,
            'anomaly_count': 0,
            'health_metrics': {}
        }
        
        # Initialize rollback checkpoints
        self.rollback_checkpoints[deployment_id] = []
        
        # Start deployment phases based on strategy
        if config.get('strategy') == 'canary':
            await self._start_canary_deployment(deployment_id, config)
        else:
            await self._start_shadow_deployment(deployment_id, config)
            
        return deployment_id
        
    async def _start_shadow_deployment(self, deployment_id, config):
        """Start shadow mode deployment phase"""
        state = self.deployment_states[deployment_id]
        component_type = state['component_type']
        version = state['version']
        
        # Activate with 0% traffic but enable shadow evaluation
        self.registry.activate_version(component_type, version, 0)
        
        # Update state
        state['status'] = 'shadow_mode'
        state['phase_start_time'] = datetime.datetime.now()
        state['shadow_evaluation_count'] = 0
        state['shadow_success_count'] = 0
        
        # Schedule phase completion check
        shadow_duration = config.get('shadow_duration_seconds', 300)  # 5 minutes default
        asyncio.create_task(self._check_shadow_phase_completion(deployment_id, shadow_duration))
        
    async def _check_shadow_phase_completion(self, deployment_id, duration):
        """Check if shadow phase can be completed successfully"""
        await asyncio.sleep(duration)
        
        if deployment_id not in self.deployment_states:
            return  # Deployment was canceled
            
        state = self.deployment_states[deployment_id]
        if state['status'] != 'shadow_mode':
            return  # Phase already changed
            
        # Check anomaly stats
        anomaly_rate = self.anomaly_detector.get_anomaly_rate(
            state['component_type'], state['version']
        )
        
        # Create checkpoint before phase transition
        self._create_rollback_checkpoint(deployment_id, 'pre_canary')
        
        if anomaly_rate <= config.get('acceptable_anomaly_rate', 0.05):  # 5% default
            # Proceed to canary phase
            await self._start_canary_phase(deployment_id)
        else:
            # Too many anomalies, fail deployment
            state['status'] = 'failed'
            state['failure_reason'] = f"Shadow mode anomaly rate too high: {anomaly_rate:.2%}"


class AnomalyDriftDetector:
    """Detects behavioral drift and anomalies in component output"""
    
    def __init__(self, config=None):
        self.comparisons = {}  # component_type -> version -> comparisons
        self.anomalies = {}  # component_type -> version -> anomalies
        self.thresholds = config or {
            'mutation_text_diff_threshold': 0.3,  # Max 30% difference in text
            'constraint_violation_threshold': 0.1,  # Max 10% new violations
            'rationale_diff_threshold': 0.5,  # Max 50% difference in rationales
        }
        
    def record_comparison(self, component_type, active_version, shadow_version, comparison, context):
        """Record a comparison between active and shadow versions"""
        if component_type not in self.comparisons:
            self.comparisons[component_type] = {}
            self.anomalies[component_type] = {}
            
        if shadow_version not in self.comparisons[component_type]:
            self.comparisons[component_type][shadow_version] = []
            self.anomalies[component_type][shadow_version] = []
            
        # Store comparison
        self.comparisons[component_type][shadow_version].append({
            'comparison': comparison,
            'context': context,
            'timestamp': datetime.datetime.now()
        })
        
        # Check for anomalies
        is_anomaly = self._detect_anomaly(comparison, context)
        if is_anomaly:
            self.anomalies[component_type][shadow_version].append({
                'comparison': comparison,
                'context': context,
                'timestamp': datetime.datetime.now(),
                'anomaly_type': is_anomaly
            })
            
    def _detect_anomaly(self, comparison, context):
        """Detect if a comparison represents an anomaly"""
        if 'mutated_text_diff' in comparison:
            if comparison['mutated_text_diff'] > self.thresholds['mutation_text_diff_threshold']:
                return 'mutation_text_drift'
                
        if 'constraint_diff' in comparison:
            if comparison['constraint_diff']['violation_rate_change'] > self.thresholds['constraint_violation_threshold']:
                return 'constraint_violation_increase'
                
        if 'rationale_diff' in comparison:
            if comparison['rationale_diff'] > self.thresholds['rationale_diff_threshold']:
                return 'rationale_drift'
                
        return None
        
    def get_anomaly_rate(self, component_type, version):
        """Get the anomaly rate for a component version"""
        if (component_type not in self.comparisons or 
            version not in self.comparisons[component_type]):
            return 0.0
            
        total_comparisons = len(self.comparisons[component_type][version])
        if total_comparisons == 0:
            return 0.0
            
        total_anomalies = len(self.anomalies[component_type][version])
        return total_anomalies / total_comparisons