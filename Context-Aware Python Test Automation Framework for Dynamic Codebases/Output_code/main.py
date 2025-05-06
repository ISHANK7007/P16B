from core.patched_edit_session import EditSession
from core.token_stream import TokenStream

# Use the new patched EditPatch version
from core.patched_edit_patch import EditPatch

class PatchOperation:
    def __init__(self, op_type, index, value):
        self.type = op_type
        self.index = index
        self.value = value

def main():
    print("🔧 Initializing Live Edit System...")

    stream = TokenStream()
    for word in ["Hello", "world", "!"]:
        stream.add_token(word)

    op = PatchOperation("replace", 0, "Hi")
    patch = EditPatch(op)

    session = EditSession(stream.tokens)
    session.add_patch(patch)

    print("✅ Final Tokens:", session.get_effective_prompt())

    print("✅ Final Tokens:", stream.tokens)

if __name__ == "__main__":
    main()
