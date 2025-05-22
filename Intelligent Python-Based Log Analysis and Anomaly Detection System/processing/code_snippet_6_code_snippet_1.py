AnomalyProcessor → Anomaly → RoutingOrchestrator
                                    ↓
      ┌─────────────────────┬──────┴───────┬─────────────────┐
      ↓                     ↓              ↓                 ↓
RiskScorer          RoutingPolicyEngine   StakeholderRegistry   NotificationGateway
                                                                       ↓
                                                              [Multiple Alert Channels]