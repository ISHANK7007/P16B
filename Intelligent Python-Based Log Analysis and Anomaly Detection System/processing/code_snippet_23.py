class FormatClusterer:
    """Cluster log formats for more efficient parser selection."""
    
    def __init__(self, max_clusters: int = 50):
        self.max_clusters = max_clusters
        self.vectorizer = None
        self.clusterer = None
        self.cluster_to_parsers = {}
        self.trained = False
        
    def train(self, log_samples: List[Tuple[str, str]]) -> None:
        """Train the clusterer on log samples with their parser names."""
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.cluster import MiniBatchKMeans
            import numpy as np
            
            # Extract logs and labels
            logs = [log for log, _ in log_samples]
            parsers = [parser for _, parser in log_samples]
            
            # Create vectorizer
            self.vectorizer = TfidfVectorizer(
                analyzer='char',
                ngram_range=(2, 4),
                max_features=500
            )
            
            # Transform logs
            X = self.vectorizer.fit_transform(logs)
            
            # Determine number of clusters (max_clusters or number of samples, whichever is smaller)
            n_clusters = min(self.max_clusters, len(logs))
            
            # Train clusterer
            self.clusterer = MiniBatchKMeans(n_clusters=n_clusters)
            self.clusterer.fit(X)
            
            # Map clusters to parsers
            cluster_labels = self.clusterer.predict(X)
            
            for i, cluster_id in enumerate(cluster_labels):
                if cluster_id not in self.cluster_to_parsers:
                    self.cluster_to_parsers[cluster_id] = Counter()
                
                self.cluster_to_parsers[cluster_id][parsers[i]] += 1
            
            self.trained = True
            
        except ImportError:
            # scikit-learn not available
            pass
    
    def predict_parsers(self, log_line: str, top_n: int = 3) -> List[str]:
        """Predict the most likely parsers for a log line based on its cluster."""
        if not self.trained or not self.vectorizer or not self.clusterer:
            return []
            
        try:
            # Transform the log line
            X = self.vectorizer.transform([log_line])
            
            # Predict cluster
            cluster_id = self.clusterer.predict(X)[0]
            
            # Get the most common parsers for this cluster
            parser_counter = self.cluster_to_parsers.get(cluster_id, Counter())
            
            # Return the top N parsers
            return [parser for parser, _ in parser_counter.most_common(top_n)]
            
        except Exception:
            return []