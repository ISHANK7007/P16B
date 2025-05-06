class EditPatch:
    """Represents a non-destructive edit overlay on the token stream"""
    def __init__(self, operation):
        self.id = str(uuid.uuid4())
        self.operation = operation
        self.timestamp = time.time()
        self.applied = False
        
    def apply_to(self, content):
        """Apply this patch to content non-destructively"""
        if self.operation.type == "insert":
            return self._apply_insert(content)
        elif self.operation.type == "replace":
            return self._apply_replace(content)
        elif self.operation.type == "delete":
            return self._apply_delete(content)
        return content