class DeEscalationTrigger(Enum):
    MANUAL_VERIFICATION = "manual_verification"       # Human confirmed benign
    ANOMALY_RECLASSIFICATION = "reclassification"     # Algorithm reclassified
    MITIGATION_VERIFIED = "mitigation_verified"       # Fix confirmed effective
    TIME_WINDOW_EXPIRED = "time_window_expired"       # Alert aged out
    DUPLICATE_RESOLUTION = "duplicate_resolution"     # Similar alert resolved
    DEPENDENCY_RESOLVED = "dependency_resolved"       # Underlying issue fixed
    CONDITIONAL_THRESHOLD = "conditional_threshold"   # Metrics returned to normal
    AUTO_REMEDIATION_SUCCESS = "auto_remediation"     # System auto-fixed issue