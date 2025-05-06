# Example telemetry integration
class SimulationTelemetry:
    def record_simulation_latency(self, provider, format_type, latency):
        # Record to Prometheus
        SIMULATION_LATENCY.labels(provider=provider, format=format_type).observe(latency)