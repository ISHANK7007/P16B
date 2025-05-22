def _apply_delta_diff(self, cached_graph, topology_changes):
    """Apply incremental changes to cached topology without full recomputation"""
    result_graph = cached_graph.clone()
    
    # Apply node additions/removals (rare in production)
    for node_change in topology_changes.node_changes:
        if node_change.is_addition:
            result_graph.add_node(node_change.node_data)
        elif node_change.is_removal:
            result_graph.remove_node(node_change.node_id)
    
    # Apply edge changes (more common - configuration/deployment changes)
    for edge_change in topology_changes.edge_changes:
        if edge_change.is_addition:
            result_graph.add_edge(edge_change.from_id, edge_change.to_id, edge_change.metadata)
        elif edge_change.is_modification:
            result_graph.update_edge_metadata(edge_change.from_id, edge_change.to_id, edge_change.metadata)
        elif edge_change.is_removal:
            result_graph.remove_edge(edge_change.from_id, edge_change.to_id)
    
    # Update property changes (most common - metrics, health status)
    for prop_change in topology_changes.property_changes:
        result_graph.update_node_property(prop_change.node_id, prop_change.key, prop_change.value)
    
    # Selectively recompute affected path metrics
    affected_paths = self._identify_affected_paths(topology_changes)
    for path in affected_paths:
        result_graph.recompute_path_metrics(path)
    
    return result_graph