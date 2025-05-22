# Example of setting up parser chains for different log sources
def setup_parser_chains(resolver: ParserResolver):
    # Chain for Linux system logs (mixed syslog and journal)
    resolver.register_chain(
        ParserChainConfig(
            name="linux_system",
            parsers=["journald", "syslog", "kernel", "fallback"],
            description="Chain for Linux system logs"
        ),
        default=False
    )
    
    # Chain for web server logs
    resolver.register_chain(
        ParserChainConfig(
            name="web_server",
            parsers=["nginx", "apache_access", "apache_error", "json"],
            description="Chain for web server logs"
        ),
        default=False
    )
    
    # Chain for application logs
    resolver.register_chain(
        ParserChainConfig(
            name="application",
            parsers=["custom_app", "json", "python_logging", "fallback"],
            description="Chain for application logs"
        ),
        default=True  # Set as default
    )
    
    # Special chain for mixed format logs
    resolver.register_chain(
        ParserChainConfig(
            name="mixed",
            parsers=["json", "syslog", "custom_app", "python_logging", "apache_access"],
            description="Chain for mixed format logs"
        ),
        default=False
    )