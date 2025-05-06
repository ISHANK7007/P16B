class HallucinationDetector:
    """Detects potential hallucinations in the generated content"""
    def __init__(self, fact_database=None):
        self.fact_database = fact_database or {}
        self.entity_extractor = EntityExtractor()
        
    def should_apply(self, tokens, metadata, tracking):
        # Apply to windows containing factual claims
        text = "".join(tokens)
        return any(marker in text.lower() for marker in 
                  ["according to", "research shows", "studies indicate", 
                   "evidence suggests", "statistics show", "data reveals"])
        
    def validate(self, tokens, metadata, tracking):
        text = "".join(tokens)
        
        # Extract entities and claims
        entities = self.entity_extractor.extract(text)
        claims = self._extract_claims(text, entities)
        
        # Check claims against fact database
        suspicious_claims = []
        for claim in claims:
            confidence = self._verify_claim(claim)
            if confidence < 0.3:  # Low confidence threshold
                suspicious_claims.append({
                    "claim": claim,
                    "confidence": confidence
                })
                
        if suspicious_claims:
            return ValidationResult(
                is_valid=False,
                type="potential_hallucination",
                severity=0.5 + (0.5 * (len(suspicious_claims) / len(claims))),
                message=f"Detected {len(suspicious_claims)} suspicious claims",
                context={
                    "suspicious_claims": suspicious_claims
                }
            )
            
        return ValidationResult(is_valid=True)