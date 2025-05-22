class MLParserClassifier:
    """Machine learning based parser classifier."""
    
    def __init__(self, vectorizer=None, model=None, training_threshold: int = 1000):
        self.vectorizer = vectorizer
        self.model = model
        self.training_data = []
        self.training_labels = []
        self.training_threshold = training_threshold
        self.trained = False
        
    def add_training_example(self, log_line: str, parser_name: str) -> None:
        """Add a training example to the classifier."""
        if not self.trained:
            self.training_data.append(log_line)
            self.training_labels.append(parser_name)
            
            # Train if we've reached the threshold
            if len(self.training_data) >= self.training_threshold:
                self.train()
    
    def train(self) -> None:
        """Train the classifier on collected examples."""
        if not self.training_data:
            return
            
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.ensemble import RandomForestClassifier
            
            # Initialize the vectorizer and model if not already done
            if self.vectorizer is None:
                self.vectorizer = TfidfVectorizer(
                    analyzer='char', 
                    ngram_range=(2, 5),
                    max_features=1000
                )
            
            if self.model is None:
                self.model = RandomForestClassifier(n_estimators=50)
            
            # Prepare data
            X = self.vectorizer.fit_transform(self.training_data)
            y = self.training_labels
            
            # Train the model
            self.model.fit(X, y)
            self.trained = True
            
            # Clear training data to save memory
            self.training_data = []
            self.training_labels = []
            
        except ImportError:
            # scikit-learn not available
            pass
    
    def predict(self, log_line: str) -> Optional[str]:
        """Predict the best parser for a log line."""
        if not self.trained or not self.model or not self.vectorizer:
            return None
            
        try:
            # Transform the log line
            X = self.vectorizer.transform([log_line])
            
            # Predict
            parser_name = self.model.predict(X)[0]
            
            # Get confidence
            probabilities = self.model.predict_proba(X)[0]
            confidence = max(probabilities)
            
            # Only return high confidence predictions
            if confidence >= 0.7:
                return parser_name
            
            return None
            
        except Exception:
            # Something went wrong with prediction
            return None