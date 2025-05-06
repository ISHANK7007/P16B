async def deduplicate_mutations(mutations):
    """Pre-process mutations to identify and deduplicate similar ones"""
    # Group mutations by content similarity
    similarity_groups = {}
    
    for mutation in mutations:
        # Create a simplified representation for comparison
        # This could be a hash of the key content or a more sophisticated similarity measure
        simplified = f"{mutation.original_prompt[:100]}_{mutation.mutated_prompt[:100]}"
        hash_key = hashlib.md5(simplified.encode()).hexdigest()
        
        if hash_key not in similarity_groups:
            similarity_groups[hash_key] = []
        
        similarity_groups[hash_key].append(mutation)
    
    # For each group, keep only one representative
    deduplicated = []
    duplication_map = {}  # Maps duplicates to their representative
    
    for group in similarity_groups.values():
        if len(group) == 1:
            # No duplicates
            deduplicated.append(group[0])
        else:
            # Keep the first as representative
            representative = group[0]
            deduplicated.append(representative)
            
            # Map duplicates to the representative
            for duplicate in group[1:]:
                duplication_map[duplicate.mutation_id] = representative.mutation_id
    
    return deduplicated, duplication_map