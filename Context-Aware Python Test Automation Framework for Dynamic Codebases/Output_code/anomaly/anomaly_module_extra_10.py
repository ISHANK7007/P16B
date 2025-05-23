┌────────────────────┐      ┌──────────────────────┐
│  Traffic Router    │◄────►│ Deployment Manager   │
└────────┬───────────┘      └──────────┬───────────┘
         │                             │
         ▼                             ▼
┌────────────────────┐      ┌──────────────────────┐
│ Component Registry │◄────►│ Anomaly Detector     │
└────────┬───────────┘      └──────────────────────┘
         │
         ▼
┌────────────────────┐      ┌──────────────────────┐
│ Shadow Mode        │◄────►│ Rollback Manager     │
│ Evaluator          │      │                      │
└────────┬───────────┘      └──────────────────────┘
         │
         ▼
┌────────────────────┐      ┌──────────────────────┐
│ Component Pool     │◄────►│ Audit Trace Recorder │
│ (Active + Shadow)  │      │                      │
└────────────────────┘      └──────────────────────┘