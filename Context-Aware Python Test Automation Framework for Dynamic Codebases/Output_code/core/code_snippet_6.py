class EventBus:
    """Simple event bus for coordinating edit events"""
    def __init__(self):
        self.subscribers = defaultdict(list)
        
    def subscribe(self, event_type, callback):
        """Subscribe to an event type"""
        self.subscribers[event_type].append(callback)
        
    def emit(self, event_type, data):
        """Emit an event to all subscribers"""
        for callback in self.subscribers[event_type]:
            callback(data)