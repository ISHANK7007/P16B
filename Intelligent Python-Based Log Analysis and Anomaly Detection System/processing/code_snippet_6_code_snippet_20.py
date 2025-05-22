class AnomalyCluster:
    """Represents a cluster of related anomalies"""
    
    def __init__(self, cluster_id: str, representative_fingerprint: str):
        self.cluster_id = cluster_id
        self.representative_fingerprint = representative_fingerprint
        self.member_fingerprints: List[str] = [representative_fingerprint]
        self.creation_time = time.time()
        self.last_update = self.creation_time
        self.evaluation_count = 0
        self.anomaly_count = 1
        self.services: Set[str] = set()
        self.is_active = True
        
    def add_member(self, fingerprint: str, service: str) -> None:
        """Add a member to this cluster"""
        if fingerprint not in self.member_fingerprints:
            self.member_fingerprints.append(fingerprint)
            self.anomaly_count += 1
        self.services.add(service)
        self.last_update = time.time()
        
    def get_age(self) -> float:
        """Get the age of this cluster in seconds"""
        return time.time() - self.creation_time
        
    def get_size(self) -> int:
        """Get the number of distinct anomalies in this cluster"""
        return len(self.member_fingerprints)

class ClusterManager:
    """Manages clusters of related anomalies for optimized evaluation"""
    
    def __init__(self, similarity_threshold: float = 0.7):
        self.clusters: Dict[str, AnomalyCluster] = {}  # cluster_id -> cluster
        self.fingerprint_to_cluster: Dict[str, str] = {}  # fingerprint -> cluster_id
        self.similarity_threshold = similarity_threshold
        self.next_cluster_id = 1
        
    def process_anomaly(self, anomaly: Anomaly) -> str:
        """
        Process an anomaly, assigning it to a cluster.
        Returns the cluster ID.
        """
        fingerprint = anomaly.fingerprint
        service = anomaly.service_name
        
        # Check if already assigned to a cluster
        if fingerprint in self.fingerprint_to_cluster:
            cluster_id = self.fingerprint_to_cluster[fingerprint]
            if cluster_id in self. clusters:
                # Update existing cluster
                cluster = self.clusters[cluster_id]
                cluster.add_member(fingerprint, service)
                return cluster_id
        
        # Find most similar existing cluster
        best_cluster_id = None
        best_similarity = 0.0
        
        for cluster_id, cluster in self.clusters.items():
            # Only consider active clusters
            if not cluster.is_active:
                continue
                
            # Calculate similarity (this would be application-specific)
            similarity = self._calculate_similarity(anomaly, cluster)
            
            if similarity > best_similarity:
                best_similarity = similarity
                best_cluster_id = cluster_id
        
        # If similar enough to an existing cluster, add to it
        if best_similarity >= self.similarity_threshold and best_cluster_id:
            cluster = self.clusters[best_cluster_id]
            cluster.add_member(fingerprint, service)
            self.fingerprint_to_cluster[fingerprint] = best_cluster_id
            return best_cluster_id
            
        # Otherwise create a new cluster
        cluster_id = f"cluster-{self.next_cluster_id}"
        self.next_cluster_id += 1
        
        new_cluster = AnomalyCluster(cluster_id, fingerprint)
        new_cluster.add_member(fingerprint, service)
        
        self.clusters[cluster_id] = new_cluster
        self.fingerprint_to_cluster[fingerprint] = cluster_id
        
        return cluster_id
    
    def _calculate_similarity(self, anomaly: Anomaly, cluster: AnomalyCluster) -> float:
        """Calculate similarity between an anomaly and a cluster"""
        # Basic implementation - would be more sophisticated in practice
        # Start with service match
        if anomaly.service_name in cluster.services:
            base_similarity = 0.5
        else:
            base_similarity = 0.0
            
        # Could incorporate more factors like:
        # - Anomaly type match
        # - Similar timestamps
        # - Semantic similarity of details
        # - Graph distance in service topology
        
        return base_similarity
    
    def get_cluster(self, cluster_id: str) -> Optional[AnomalyCluster]:
        """Get a cluster by ID"""
        return self.clusters.get(cluster_id)
        
    def get_cluster_for_fingerprint(self, fingerprint: str) -> Optional[AnomalyCluster]:
        """Get the cluster containing a fingerprint"""
        cluster_id = self.fingerprint_to_cluster.get(fingerprint)
        if not cluster_id:
            return None
        return self.clusters.get(cluster_id)
        
    def mark_cluster_processed(self, cluster_id: str) -> None:
        """Mark a cluster as having been processed by the escalation engine"""
        if cluster_id in self.clusters:
            self.clusters[cluster_id].evaluation_count += 1
            
    def close_inactive_clusters(self, max_age_seconds: float = 3600) -> int:
        """Close clusters that haven't been updated recently"""
        now = time.time()
        closed_count = 0
        
        for cluster_id, cluster in self.clusters.items():
            if cluster.is_active and now - cluster.last_update > max_age_seconds:
                cluster.is_active = False
                closed_count += 1
                
        return closed_count