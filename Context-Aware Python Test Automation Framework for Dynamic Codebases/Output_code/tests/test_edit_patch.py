import uuid
from core.patched_edit_patch import EditPatch
from core.patched_edit_session import EditSession

class DummyOp:
    def __init__(self, op_type, index, value):
        self.type = op_type
        self.index = index
        self.value = value

def test_edit_patch_insert():
    op = DummyOp("insert", 1, "world")
    patch = EditPatch(op)
    result = patch.apply_to(["Hello", "!"])
    assert result == ["Hello", "world", "!"]

def test_edit_patch_replace():
    op = DummyOp("replace", 0, "Hi")
    patch = EditPatch(op)
    result = patch.apply_to(["Hello", "world"])
    assert result == ["Hi", "world"]

def test_edit_session_patch_application():
    template = ["Goodbye", "Earth"]
    session = EditSession(template)
    op = DummyOp("replace", 1, "World")
    patch = EditPatch(op)
    session.add_patch(patch)
    final = session.get_effective_prompt()
    assert final == ["Goodbye", "World"]
