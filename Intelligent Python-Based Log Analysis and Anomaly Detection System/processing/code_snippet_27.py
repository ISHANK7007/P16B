class OptimizedFieldExtractor:
    """Optimized field extraction with caching."""
    
    def __init__(self):
        self.extractors = {}
        
    def register_extractor(self, field_name: str, pattern: str, transform: Optional[Callable] = None) -> None:
        """Register a field extractor."""
        self.extractors[field_name] = {
            'pattern': re.compile(pattern),
            'transform': transform
        }
    
    @lru_cache(maxsize=1000)
    def extract(self, log_line: str, field_name: str) -> Optional[Any]:
        """Extract a field from a log line with caching."""
        extractor = self.extractors.get(field_name)
        if not extractor:
            return None
            
        match = extractor['pattern'].search(log_line)
        if not match:
            return None
            
        value = match.group(1) if match.groups() else match.group(0)
        
        # Apply transform if available
        if extractor['transform'] and value is not None:
            try:
                value = extractor['transform'](value)
            except Exception:
                pass
                
        return value