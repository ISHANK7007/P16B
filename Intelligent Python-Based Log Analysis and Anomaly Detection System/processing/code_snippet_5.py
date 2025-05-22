from typing import List, Optional, Type, Tuple, Set
from dataclasses import dataclass

@dataclass
class ParserChainConfig:
    """Configuration for a parser chain."""
    name: str
    parsers: List[str]  # Parser names in priority order
    description: str = ""

class ParserResolver:
    """Resolves the appropriate parser for a given log line using fallback chains."""
    
    def __init__(self):
        self._chains: Dict[str, ParserChainConfig] = {}
        self._default_chain: Optional[str] = None
    
    def register_chain(self, config: ParserChainConfig, default: bool = False) -> None:
        """Register a parser chain configuration."""
        self._chains[config.name] = config
        if default:
            self._default_chain = config.name
    
    def get_chain(self, name: str) -> Optional[ParserChainConfig]:
        """Get a parser chain by name."""
        return self._chains.get(name)
    
    def get_default_chain(self) -> Optional[ParserChainConfig]:
        """Get the default parser chain."""
        if self._default_chain:
            return self._chains.get(self._default_chain)
        return None
    
    def resolve(self, log_line: str, chain_name: Optional[str] = None) -> Tuple[Optional[ParsedLogEntry], Optional[str]]:
        """
        Attempt to parse a log line using the specified chain or the default chain.
        
        Returns:
            Tuple of (parsed_entry, parser_name) or (None, None) if parsing failed
        """
        # Get the chain to use
        chain = None
        if chain_name:
            chain = self.get_chain(chain_name)
        if not chain and self._default_chain:
            chain = self.get_chain(self._default_chain)
        if not chain:
            # Try all parsers if no chain is specified
            return self._try_all_parsers(log_line)
        
        # Try parsers in the chain's order
        return self._try_parser_chain(log_line, chain)
    
    def _try_parser_chain(self, log_line: str, chain: ParserChainConfig) -> Tuple[Optional[ParsedLogEntry], Optional[str]]:
        """Try parsers in the order specified in the chain."""
        for parser_name in chain.parsers:
            parser_class = ParserRegistry.get_parser(parser_name)
            if not parser_class:
                continue
                
            parser = parser_class()
            if parser.can_parse(log_line):
                entry = parser.parse(log_line)
                if entry:
                    return entry, parser_name
        
        return None, None
        
    def _try_all_parsers(self, log_line: str) -> Tuple[Optional[ParsedLogEntry], Optional[str]]:
        """Try all available parsers in priority order based on specificity score."""
        # Sort parsers by specificity score (higher is more specific)
        parser_classes = sorted(
            ParserRegistry.get_all_parsers().items(),
            key=lambda x: self._calculate_specificity(x[1], log_line),
            reverse=True
        )
        
        for parser_name, parser_class in parser_classes:
            parser = parser_class()
            entry = parser.parse(log_line)
            if entry:
                return entry, parser_name
        
        return None, None
    
    def _calculate_specificity(self, parser_class: Type[LogParser], log_line: str) -> int:
        """
        Calculate a specificity score for a parser on a given log line.
        Higher scores indicate a more specific match.
        """
        # Base score is 0
        score = 0
        
        # If the parser declares it can parse the line, add points
        if parser_class.can_parse(log_line):
            score += 100
            
        # More specific patterns get higher scores
        for pattern in parser_class.format_patterns:
            if pattern.search(log_line):
                # More complex patterns are likely more specific
                pattern_complexity = len(pattern.pattern)
                score += pattern_complexity // 10
                
                # If the pattern has named groups, it's more specific
                named_groups = getattr(pattern, 'groupindex', {})
                score += len(named_groups) * 5
                
        return score