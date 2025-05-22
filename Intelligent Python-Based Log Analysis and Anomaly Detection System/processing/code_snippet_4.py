# In setup.py
setup(
    # ... other configuration ...
    entry_points={
        'log_parsers': [
            'json = your_package.parsers.json:JsonLogParser',
            'apache_access = your_package.parsers.apache:ApacheAccessLogParser',
            # Add more parsers here
        ],
    },
)