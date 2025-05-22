class FileLogIngestor:
    def stream(self):
        return ["log line 1", "log line 2"]

    def normalize(self, logs):
        return [{"timestamp": "2025-05-08T12:00:00", "message": log} for log in logs]

    def tag(self, normalized_logs):
        for log in normalized_logs:
            log["source"] = "file"
        return normalized_logs
