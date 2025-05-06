    # Replace all invocations
    processed = re.sub(pattern, replace_invocation, text)
    
    return processed, results