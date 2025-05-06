class DirectedGraph:
    """
    A simple directed graph implementation for tracking relationships
    """
    def __init__(self):
        self.nodes = set()
        self.edges = {}  # node -> [node]
        self.edge_metadata = {}  # (node1, node2) -> metadata
        
    def add_node(self, node):
        self.nodes.add(node)
        if node not in self.edges:
            self.edges[node] = []
            
    def add_edge(self, from_node, to_node, metadata=None):
        """Add a directed edge with optional metadata"""
        self.add_node(from_node)
        self.add_node(to_node)
        self.edges[from_node].append(to_node)
        
        if metadata:
            edge_key = (from_node, to_node)
            self.edge_metadata[edge_key] = metadata
            
    def get_ancestors(self, node, max_depth=None):
        """Get all ancestors of a node (nodes with paths to this node)"""
        ancestors = set()
        self._collect_ancestors(node, ancestors, 0, max_depth)
        return ancestors
        
    def _collect_ancestors(self, node, ancestors_set, current_depth, max_depth):
        """Recursively collect ancestors"""
        if max_depth is not None and current_depth >= max_depth:
            return
            
        for source, targets in self.edges.items():
            if node in targets and source not in ancestors_set:
                ancestors_set.add(source)
                self._collect_ancestors(source, ancestors_set, current_depth + 1, max_depth)
                
    def get_descendants(self, node, max_depth=None):
        """Get all descendants of a node (nodes reachable from this node)"""
        descendants = set()
        self._collect_descendants(node, descendants, 0, max_depth)
        return descendants
        
    def _collect_descendants(self, node, descendants_set, current_depth, max_depth):
        """Recursively collect descendants"""
        if max_depth is not None and current_depth >= max_depth:
            return
            
        if node in self.edges:
            for target in self.edges[node]:
                if target not in descendants_set:
                    descendants_set.add(target)
                    self._collect_descendants(target, descendants_set, current_depth + 1, max_depth)