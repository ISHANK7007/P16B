@register_parser(
    name="json", 
    patterns=[r'^\s*\{.*\}\s*$']
)
class JsonLogParser(LogParser):
    """Parser for JSON formatted logs."""
    
    def parse(self, log_line: str) -> Optional[ParsedLogEntry]:
        try:
            import json
            data = json.loads(log_line)
            
            # Extract common fields with sensible defaults
            timestamp = data.get('timestamp', data.get('time', data.get('@timestamp')))
            if isinstance(timestamp, str):
                # Handle different timestamp formats (simplified here)
                timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            else:
                timestamp = datetime.now()
                
            return ParsedLogEntry(
                timestamp=timestamp,
                level=data.get('level', data.get('severity', 'INFO')),
                message=data.get('message', data.get('msg', '')),
                source=data.get('source', data.get('logger', '')),
                fields=data
            )
        except Exception as e:
            # Log the error or handle it according to your error handling strategy
            return None

@register_parser(
    name="apache_access", 
    patterns=[r'^\S+ - \S+ \[\d+/\w+/\d+:\d+:\d+:\d+ [\+\-]\d+\] ".*" \d+ \d+']
)
class ApacheAccessLogParser(LogParser):
    """Parser for Apache access logs."""
    
    def parse(self, log_line: str) -> Optional[ParsedLogEntry]:
        # Apache log format: %h %l %u %t \"%r\" %>s %b \"%{Referer}i\" \"%{User-agent}i\"
        pattern = re.compile(
            r'(\S+) - (\S+) \[([^]]+)\] "([^"]*)" (\d+) (\d+|-) "([^"]*)" "([^"]*)"'
        )
        match = pattern.match(log_line)
        
        if not match:
            return None
            
        ip, auth_user, time_str, request, status, size, referer, user_agent = match.groups()
        
        try:
            # Parse the timestamp
            timestamp = datetime.strptime(time_str, "%d/%b/%Y:%H:%M:%S %z")
            
            # Parse the request
            method, path, protocol = request.split(" ", 2) if " " in request else (request, "", "")
            
            return ParsedLogEntry(
                timestamp=timestamp,
                level="INFO",  # Apache logs don't have a level
                message=f"{method} {path} {status}",
                source="apache_access",
                fields={
                    "ip": ip,
                    "user": auth_user if auth_user != "-" else None,
                    "method": method,
                    "path": path,
                    "protocol": protocol,
                    "status": int(status),
                    "size": int(size) if size != "-" else 0,
                    "referer": referer if referer != "-" else None,
                    "user_agent": user_agent if user_agent != "-" else None
                }
            )
        except Exception as e:
            # Log the error
            return None