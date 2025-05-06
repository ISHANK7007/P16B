class SemanticASTChunkingEngine:
    """
    Chunks prompt diffs based on semantic abstract syntax tree (AST) analysis
    to optimize storage and transmission of edit operations.
    """
    def __init__(self):
        self.parser = SimplePromptParser()
        self.chunk_store = {}
        self.shared_chunks = {}
        
    def chunk_diff(self, diff_operation):
        """Break down a diff operation into semantic chunks"""
        # Parse the content into semantic units
        if diff_operation.operation_type == "replace":
            old_ast = self.parser.parse(diff_operation.old_content)
            new_ast = self.parser.parse(diff_operation.new_content)
            
            # Find semantic boundaries for chunking
            chunk_boundaries = self._find_chunk_boundaries(old_ast, new_ast)
            
            # Create chunks based on boundaries
            chunks = self._create_chunks(
                diff_operation, chunk_boundaries, old_ast, new_ast)
                
            # Deduplicate chunks and store references
            chunks = self._deduplicate_chunks(chunks)
            
            return {
                "operation_id": diff_operation.id,
                "chunks": [chunk.id for chunk in chunks],
                "chunk_map": self._create_chunk_map(chunks, diff_operation)
            }
        else:
            # For simpler operations like insert/delete, use basic chunking
            return self._basic_chunk(diff_operation)
            
    def _find_chunk_boundaries(self, old_ast, new_ast):
        """Find optimal semantic boundaries for chunking"""
        boundaries = []
        
        # Look for logical boundaries like:
        # - Statement boundaries
        # - Block boundaries
        # - List item boundaries
        # - Paragraph boundaries
        
        for node in new_ast.nodes:
            if node.type in ["block_start", "block_end", "paragraph", "statement"]:
                boundaries.append(node.span)
                
        # Ensure boundaries don't cross semantic units
        boundaries = self._optimize_boundaries(boundaries, new_ast)
        
        return boundaries
        
    def _create_chunks(self, diff_operation, boundaries, old_ast, new_ast):
        """Create chunks based on semantic boundaries"""
        chunks = []
        
        current_pos = 0
        for boundary in sorted(boundaries):
            if boundary.start > current_pos:
                # Create a chunk from current_pos to boundary.start
                chunk_content = diff_operation.new_content[current_pos:boundary.start]
                chunk = DiffChunk(
                    content=chunk_content,
                    semantic_type=self._determine_semantic_type(
                        chunk_content, new_ast, current_pos, boundary.start),
                    position=current_pos,
                    length=boundary.start - current_pos
                )
                chunks.append(chunk)
                
            current_pos = boundary.start
            
        # Add the final chunk if needed
        if current_pos < len(diff_operation.new_content):
            chunk_content = diff_operation.new_content[current_pos:]
            chunk = DiffChunk(
                content=chunk_content,
                semantic_type=self._determine_semantic_type(
                    chunk_content, new_ast, current_pos, len(diff_operation.new_content)),
                position=current_pos,
                length=len(diff_operation.new_content) - current_pos
            )
            chunks.append(chunk)
            
        return chunks
        
    def _deduplicate_chunks(self, chunks):
        """Deduplicate chunks to save memory"""
        result = []
        
        for chunk in chunks:
            # Check if similar chunk already exists
            if chunk.content in self.shared_chunks:
                # Reuse existing chunk
                existing_chunk = self.shared_chunks[chunk.content]
                result.append(existing_chunk)
            else:
                # Store new chunk
                self.chunk_store[chunk.id] = chunk
                self.shared_chunks[chunk.content] = chunk
                result.append(chunk)
                
        return result