class MutationBacktraceMap:
    """
    Tracks the origin and evolution of text spans across dialogue turns and mutations.
    Maintains a directed graph of transformations with fingerprinting for provenance.
    """
    def __init__(self):
        self.span_registry = {}  # Maps span_id to SpanMetadata
        self.transformation_graph = DirectedGraph()  # Tracks mutation relationships
        self.context_dependencies = {}  # Maps span_id to dependent span_ids
        self.violation_records = []  # History of detected violations
        
    def register_span(self, text, start_pos, end_pos, turn_id, metadata=None):
        """Register a new text span and assign it a fingerprint ID"""
        span_id = self._generate_fingerprint(text, turn_id)
        
        self.span_registry[span_id] = SpanMetadata(
            id=span_id,
            text=text,
            start_pos=start_pos,
            end_pos=end_pos,
            turn_id=turn_id,
            creation_timestamp=time.time(),
            metadata=metadata or {}
        )
        
        return span_id
        
    def track_mutation(self, original_span_id, new_text, new_start, new_end, 
                      mutation_id, operation_type, turn_id):
        """
        Track a mutation from one span to another, preserving lineage
        Returns the new span_id
        """
        new_span_id = self._generate_fingerprint(new_text, turn_id)
        
        # Register the new span
        self.span_registry[new_span_id] = SpanMetadata(
            id=new_span_id,
            text=new_text,
            start_pos=new_start,
            end_pos=new_end,
            turn_id=turn_id,
            creation_timestamp=time.time(),
            parent_id=original_span_id,
            mutation_id=mutation_id,
            operation_type=operation_type,
            metadata={}
        )
        
        # Add to transformation graph
        self.transformation_graph.add_edge(
            original_span_id, 
            new_span_id, 
            {
                "mutation_id": mutation_id,
                "operation": operation_type,
                "turn_id": turn_id,
                "timestamp": time.time()
            }
        )
        
        # Inherit context dependencies
        if original_span_id in self.context_dependencies:
            self.context_dependencies[new_span_id] = self.context_dependencies[original_span_id].copy()
            
        return new_span_id
        
    def register_dependency(self, dependent_span_id, referenced_span_id, dependency_type):
        """Register that one span depends on another span"""
        if dependent_span_id not in self.context_dependencies:
            self.context_dependencies[dependent_span_id] = set()
            
        self.context_dependencies[dependent_span_id].add({
            "referenced_span": referenced_span_id,
            "type": dependency_type,
            "timestamp": time.time()
        })
        
    def trace_span_history(self, span_id):
        """
        Trace the complete transformation history of a span
        Returns a list of spans in chronological order
        """
        history = []
        current_id = span_id
        
        while current_id:
            if current_id in self.span_registry:
                span_data = self.span_registry[current_id]
                history.append(span_data)
                current_id = span_data.parent_id
            else:
                break
                
        return list(reversed(history))  # Chronological order
        
    def get_dependent_spans(self, span_id, recursive=False):
        """
        Get all spans that depend on this span
        If recursive=True, also include spans that depend on those spans
        """
        dependents = set()
        
        # Find all spans that directly depend on this span
        for dependent_id, dependencies in self.context_dependencies.items():
            for dependency in dependencies:
                if dependency["referenced_span"] == span_id:
                    dependents.add(dependent_id)
                    
        # Recursively find spans that depend on dependents
        if recursive and dependents:
            for dependent_id in list(dependents):
                nested_dependents = self.get_dependent_spans(dependent_id, recursive=True)
                dependents.update(nested_dependents)
                
        return dependents
        
    def record_violation(self, span_id, violation_type, description, severity):
        """Record a constraint violation for a span"""
        violation = {
            "span_id": span_id,
            "violation_type": violation_type,
            "description": description,
            "severity": severity,
            "timestamp": time.time(),
            "span_history": self.trace_span_history(span_id),
            "affected_dependents": list(self.get_dependent_spans(span_id, recursive=True))
        }
        
        self.violation_records.append(violation)
        return violation
        
    def _generate_fingerprint(self, text, turn_id):
        """Generate a unique deterministic fingerprint for a text span"""
        # Use a combination of text hash and turn_id for uniqueness
        text_hash = hashlib.md5(text.encode('utf-8')).hexdigest()
        return f"span_{turn_id}_{text_hash[:12]}"