import time
import uuid

class EditPatch:
    """Represents a non-destructive edit overlay on the token stream"""
    def __init__(self, operation):
        self.id = str(uuid.uuid4())
        self.operation = operation
        self.timestamp = time.time()
        self.applied = False

    def apply_to(self, content):
        if self.operation.type == "insert":
            return self._apply_insert(content)
        elif self.operation.type == "replace":
            return self._apply_replace(content)
        else:
            return content

    def _apply_insert(self, content):
        return content[:self.operation.index] + [self.operation.value] + content[self.operation.index:]

    def _apply_replace(self, content):
        result = content.copy()
        result[self.operation.index] = self.operation.value
        return result
