class Anomaly:
    def __init__(self, id='anomaly-001', message='Test anomaly'):
        self.id = id
        self.message = message

    def __repr__(self):
        return f"<Anomaly id={self.id} message={self.message}>"