from functools import lru_cache
import re

class CompiledRegexParser(LogParser):
    """Base class for parsers with compiled regular expressions."""
    
    # Class variables
    name: ClassVar[str]
    format_patterns: ClassVar[List[re.Pattern]]
    
    # Compiled expressions stored as class variables
    _compiled_expressions: ClassVar[Dict[str, re.Pattern]] = {}
    
    @classmethod
    def compile_expressions(cls) -> None:
        """Compile all regular expressions used by this parser."""
        # Override in subclasses to compile expressions
        pass
    
    @lru_cache(maxsize=1000)
    def _cached_match(self, pattern_key: str, log_line: str) -> Optional[re.Match]:
        """Cached regex matching for better performance."""
        pattern = self._compiled_expressions.get(pattern_key)
        if not pattern:
            return None
            
        return pattern.match(log_line)