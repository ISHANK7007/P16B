from collections import defaultdict

class ExpiringCounterMap:
    def __init__(self, ttl_seconds=300):
        self.data = {}
        self.ttl = ttl_seconds

    def increment(self, key):
        self.data[key] = self.data.get(key, 0) + 1

    def get(self, key):
        return self.data.get(key, 0)

class EscalationRuleIndex:
    def __init__(self):
        # Primary index by service + criticality
        self.rule_lookup = defaultdict(list)
        # Precompiled rule evaluators
        self.evaluators = {}
        # Frequency counters for fast threshold checks
        self.counters = ExpiringCounterMap()
    
    def add_rule(self, rule):
        # Optimize rule storage and compilation
        key = (rule.service_pattern, rule.criticality)
        self.rule_lookup[key].append(rule.id)
        self.evaluators[rule.id] = compile_rule(rule)
    
    def find_matching_rules(self, alert_batch):
        # Fast multi-alert rule matching
        result = {}
        for alert in alert_batch:
            key = (alert.service_name, alert.criticality)
            candidates = self.rule_lookup.get(key, [])
            result[alert.id] = [r for r in candidates if self.evaluators[r](alert)]
        return result