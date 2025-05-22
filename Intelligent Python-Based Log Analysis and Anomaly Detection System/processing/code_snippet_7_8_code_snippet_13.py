def validate_syntax(rule_text):
    # Use parser to check grammar conformance
    try:
        token_stream = lexer.tokenize(rule_text)
        ast = parser.parse(token_stream)
        return ValidationResult(True)
    except ParseError as e:
        return ValidationResult(False, errors=[f"Syntax error at line {e.line}, column {e.column}: {e.message}"])