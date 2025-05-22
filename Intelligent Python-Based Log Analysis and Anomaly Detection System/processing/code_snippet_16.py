import sqlite3
from datetime import datetime, timedelta

class ParserAuditLog:
    """Database logging for parser traces and conflicts."""
    
    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self._create_tables()
    
    def _create_tables(self) -> None:
        """Create necessary tables if they don't exist."""
        cursor = self.conn.cursor()
        
        # Table for storing parsing attempts
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS parser_traces (
            trace_id TEXT PRIMARY KEY,
            timestamp TEXT,
            raw_log TEXT,
            selected_parser TEXT,
            parsing_time_ms REAL,
            conflict_detected INTEGER,
            conflict_resolution TEXT,
            trace_data TEXT
        )
        """)
        
        # Table for storing parser conflicts
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS parser_conflicts (
            conflict_id INTEGER PRIMARY KEY AUTOINCREMENT,
            trace_id TEXT,
            timestamp TEXT,
            log_hash TEXT,
            conflicting_parsers TEXT,
            resolution TEXT,
            FOREIGN KEY (trace_id) REFERENCES parser_traces (trace_id)
        )
        """)
        
        # Table for tracking parser performance
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS parser_performance (
            parser_name TEXT,
            date TEXT,
            attempts INTEGER,
            successes INTEGER,
            failures INTEGER,
            errors INTEGER,
            avg_confidence REAL,
            avg_time_ms REAL,
            PRIMARY KEY (parser_name, date)
        )
        """)
        
        self.conn.commit()
    
    def log_trace(self, trace: ParserTrace) -> None:
        """Log a parser trace to the database."""
        cursor = self.conn.cursor()
        
        # Convert trace to JSON for storage
        trace_data = json.dumps(trace.to_dict())
        
        cursor.execute("""
        INSERT INTO parser_traces 
        (trace_id, timestamp, raw_log, selected_parser, parsing_time_ms, conflict_detected, conflict_resolution, trace_data)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            trace.trace_id,
            trace.timestamp.isoformat(),
            trace.raw_log,
            trace.selected_parser,
            trace.parsing_time_ms,
            1 if trace.conflict_detected else 0,
            trace.conflict_resolution,
            trace_data
        ))
        
        # If there was a conflict, log it separately
        if trace.conflict_detected:
            # Create a simple hash of the log line
            import hashlib
            log_hash = hashlib.md5(trace.raw_log.encode()).hexdigest()
            
            # Get the conflicting parsers
            conflicting_parsers = [a.parser_name for a in trace.get_successful_attempts()]
            
            cursor.execute("""
            INSERT INTO parser_conflicts
            (trace_id, timestamp, log_hash, conflicting_parsers, resolution)
            VALUES (?, ?, ?, ?, ?)
            """, (
                trace.trace_id,
                trace.timestamp.isoformat(),
                log_hash,
                ",".join(conflicting_parsers),
                trace.conflict_resolution
            ))
        
        # Update parser performance stats
        today = datetime.now().date().isoformat()
        
        for attempt in trace.attempts:
            # Check if we have an entry for this parser today
            cursor.execute("""
            SELECT * FROM parser_performance 
            WHERE parser_name = ? AND date = ?
            """, (attempt.parser_name, today))
            
            row = cursor.fetchone()
            
            if row:
                # Update existing entry
                success = 1 if attempt.result == ParserResult.SUCCESS else 0
                failure = 1 if attempt.result in (ParserResult.REJECTED, ParserResult.PARTIAL) else 0
                error = 1 if attempt.result == ParserResult.ERROR else 0
                
                cursor.execute("""
                UPDATE parser_performance
                SET attempts = attempts + 1,
                    successes = successes + ?,
                    failures = failures + ?,
                    errors = errors + ?,
                    avg_confidence = (avg_confidence * attempts + ?) / (attempts + 1),
                    avg_time_ms = (avg_time_ms * attempts + ?) / (attempts + 1)
                WHERE parser_name = ? AND date = ?
                """, (
                    success,
                    failure,
                    error,
                    attempt.confidence,
                    attempt.duration_ms,
                    attempt.parser_name,
                    today
                ))
            else:
                # Create new entry
                success = 1 if attempt.result == ParserResult.SUCCESS else 0
                failure = 1 if attempt.result in (ParserResult.REJECTED, ParserResult.PARTIAL) else 0
                error = 1 if attempt.result == ParserResult.ERROR else 0
                
                cursor.execute("""
                INSERT INTO parser_performance
                (parser_name, date, attempts, successes, failures, errors, avg_confidence, avg_time_ms)
                VALUES (?, ?, 1, ?, ?, ?, ?, ?)
                """, (
                    attempt.parser_name,
                    today,
                    success,
                    failure,
                    error,
                    attempt.confidence,
                    attempt.duration_ms
                ))
        
        self.conn.commit()
    
    def get_recent_conflicts(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent parser conflicts."""
        cursor = self.conn.cursor()
        
        cursor.execute("""
        SELECT * FROM parser_conflicts
        ORDER BY timestamp DESC
        LIMIT ?
        """, (limit,))
        
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def get_recurring_conflicts(self, days: int = 7, min_occurrences: int = 3) -> List[Dict[str, Any]]:
        """Get recurring parser conflicts over the past days."""
        cursor = self.conn.cursor()
        
        # Get conflicts with the same log hash that occurred multiple times
        min_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        cursor.execute("""
        SELECT log_hash, COUNT(*) as occurrences, GROUP_CONCAT(DISTINCT conflicting_parsers) as parsers
        FROM parser_conflicts
        WHERE timestamp > ?
        GROUP BY log_hash
        HAVING occurrences >= ?
        ORDER BY occurrences DESC
        """, (min_date, min_occurrences))
        
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def get_parser_performance(self, days: int = 7) -> Dict[str, Dict[str, Any]]:
        """Get parser performance statistics over the past days."""
        cursor = self.conn.cursor()
        
        min_date = (datetime.now() - timedelta(days=days)).date().isoformat()
        
        cursor.execute("""
        SELECT parser_name,
               SUM(attempts) as total_attempts,
               SUM(successes) as total_successes,
               SUM(failures) as total_failures,
               SUM(errors) as total_errors,
               AVG(avg_confidence) as overall_confidence,
               AVG(avg_time_ms) as overall_time_ms
        FROM parser_performance
        WHERE date >= ?
        GROUP BY parser_name
        ORDER BY total_attempts DESC
        """, (min_date,))
        
        results = {}
        for row in cursor.fetchall():
            parser_name = row[0]
            results[parser_name] = {
                "attempts": row[1],
                "successes": row[2],
                "failures": row[3],
                "errors": row[4],
                "success_rate": row[2] / row[1] if row[1] > 0 else 0,
                "avg_confidence": row[5],
                "avg_time_ms": row[6]
            }
        
        return results
    
    def close(self) -> None:
        """Close the database connection."""
        self.conn.close()