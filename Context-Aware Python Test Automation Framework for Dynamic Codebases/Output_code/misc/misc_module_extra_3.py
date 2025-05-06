@dataclass
class MutationAuditEvent:
    timestamp: datetime
    event_type: str  # "mutation", "arbitration", "constraint_violation", etc.
    component: str   # Component that generated the event
    prompt_id: str   # ID of the affected prompt
    details: Dict    # Event-specific details
    persona: Optional[PersonaType] = None
    severity: int = 1
    
@dataclass
class MutationAuditTrace:
    session_id: str
    start_time: datetime
    prompt_format: PromptFormat
    events: List[MutationAuditEvent] = field(default_factory=list)
    final_mutation: Optional[PromptMutation] = None
    persona_involved: List[PersonaType] = field(default_factory=list)
    # Export to multiple formats
    def to_json(self) -> str: ...
    def to_sarif(self) -> str: ...
    def to_markdown(self) -> str: ...