class SyntheticAnomalyGenerator:
    """Generates realistic synthetic anomalies for testing"""
    
    def __init__(self):
        self.templates = {}
        self.fingerprint_generator = TestFingerprintGenerator()
        self.load_default_templates()
    
    def load_default_templates(self):
        """Load default anomaly templates"""
        self.templates = {
            "high_cpu": {
                "type": AnomalyType.PERFORMANCE,
                "service_pattern": "compute-*",
                "criticality": ServiceCriticality.HIGH,
                "parameters": {
                    "cpu_threshold": 90,
                    "duration": 300
                }
            },
            "memory_leak": {
                "type": AnomalyType.PERFORMANCE,
                "service_pattern": "*",
                "criticality": ServiceCriticality.MEDIUM,
                "parameters": {
                    "growth_rate": "linear",
                    "leak_size_mb": 500
                }
            },
            "security_breach": {
                "type": AnomalyType.SECURITY,
                "service_pattern": "auth-*",
                "criticality": ServiceCriticality.CRITICAL,
                "parameters": {
                    "affected_systems": ["database", "api"],
                    "breach_type": "unauthorized_access"
                }
            },
            "service_degradation": {
                "type": AnomalyType.AVAILABILITY,
                "service_pattern": "*-api",
                "criticality": ServiceCriticality.HIGH,
                "parameters": {
                    "error_ratio": 0.15,
                    "latency_increase": 2.5
                }
            },
            # More templates...
        }
    
    async def generate(self, template, context=None):
        """Generate a synthetic anomaly from template and context"""
        if isinstance(template, str):
            if template not in self.templates:
                raise ValueError(f"Unknown template: {template}")
            template_data = self.templates[template]
        else:
            template_data = template
            
        # Apply context overrides
        template_data = self._apply_context(template_data, context or {})
        
        # Generate basic anomaly
        anomaly = Anomaly(
            id=str(uuid.uuid4()),
            type=template_data["type"],
            service_name=self._generate_service_name(template_data["service_pattern"]),
            criticality=template_data["criticality"],
            timestamp=datetime.utcnow(),
            confidence=random.uniform(0.7, 0.99)
        )
        
        # Generate fingerprint
        anomaly.fingerprint = self.fingerprint_generator.generate_fingerprint(
            anomaly, template_data
        )
        
        # Add details from parameters
        anomaly.details = template_data["parameters"]
        
        # Add synthetic logs if requested
        if context and context.get("generate_logs", False):
            anomaly.logs = self._generate_sample_logs(anomaly)
            
        return anomaly
    
    def _apply_context(self, template, context):
        """Apply context overrides to template"""
        result = copy.deepcopy(template)
        
        # Override basic properties
        for key in ["type", "service_pattern", "criticality"]:
            if key in context:
                result[key] = context[key]
                
        # Merge parameters
        if "parameters" in context:
            result["parameters"].update(context["parameters"])
            
        return result
    
    def _generate_service_name(self, pattern):
        """Generate a realistic service name from pattern"""
        if "*" not in pattern:
            return pattern
            
        # Handle patterns like "auth-*"
        if pattern.endswith("*"):
            prefix = pattern[:-1]
            suffixes = ["service", "api", "worker", "processor", "manager"]
            return f"{prefix}{random.choice(suffixes)}"
            
        # Handle patterns like "*-api"
        if pattern.startswith("*"):
            suffix = pattern[1:]
            prefixes = ["user", "payment", "order", "catalog", "search"]
            return f"{random.choice(prefixes)}{suffix}"
            
        # Handle patterns with * in middle
        parts = pattern.split("*")
        middle_options = ["internal", "external", "batch", "realtime"]
        return f"{parts[0]}{random.choice(middle_options)}{parts[1]}"