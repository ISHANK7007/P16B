class TransformationPipeline:
    def apply(self, logs):
        # Example: Convert all messages to uppercase
        for log in logs:
            log["message"] = log["message"].upper()
        return logs
