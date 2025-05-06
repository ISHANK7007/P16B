# Cost limiter
async def enforce_budget_controls(simulator, daily_budget=100.0):
    while True:
        current_spend = get_daily_spend()  # Hypothetical function
        if current_spend > daily_budget:
            # Pause non-critical workloads
            # Redirect to cheaper providers
            # Send alerts
        await asyncio.sleep(300)  # Check every 5 minutes