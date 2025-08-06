import sqlite3
import re
import os
import tempfile
import logging
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path


class SQLLogDatabase:
    """SQLite database manager for log analysis."""
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize database connection."""
        if db_path is None:
            self.db_path = os.path.join(tempfile.gettempdir(), 'log_analyzer.db')
        else:
            self.db_path = db_path
        self.connection = None
        self._connect()
    
    def _connect(self):
        """Establish database connection."""
        try:
            self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self.connection.row_factory = sqlite3.Row  # Enable dict-like access
            self.connection.execute("PRAGMA foreign_keys = ON")
        except Exception as e:
            logging.error(f"Failed to connect to database: {e}")
            raise
    
    def close(self):
        """Close database connection."""
        if self.connection:
            self.connection.close()
            self.connection = None
    
    def create_table(self, table_name: str) -> bool:
        """Create a logs table."""
        try:
            sql = f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                program TEXT,
                message TEXT,
                level TEXT,
                full_line TEXT NOT NULL,
                source_file TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
            self.connection.execute(sql)
            
            # Create indexes for better query performance
            self.connection.execute(f"CREATE INDEX IF NOT EXISTS idx_{table_name}_timestamp ON {table_name}(timestamp)")
            self.connection.execute(f"CREATE INDEX IF NOT EXISTS idx_{table_name}_program ON {table_name}(program)")
            self.connection.execute(f"CREATE INDEX IF NOT EXISTS idx_{table_name}_level ON {table_name}(level)")
            
            self.connection.commit()
            return True
        except Exception as e:
            logging.error(f"Failed to create table {table_name}: {e}")
            return False
    
    def import_log_file(self, filepath: Path, table_name: str) -> Dict[str, Any]:
        """Import log file into database table."""
        if not filepath.exists():
            raise FileNotFoundError(f"File not found: {filepath}")
        
        # Create table
        if not self.create_table(table_name):
            raise Exception(f"Failed to create table {table_name}")
        
        try:
            lines = filepath.read_text(encoding="utf-8", errors="ignore").splitlines()
        except Exception as e:
            raise Exception(f"Error reading file {filepath}: {e}")
        
        imported_count = 0
        failed_count = 0
        
        # Patterns for parsing log lines
        timestamp_pattern = re.compile(r'(\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2})')
        program_pattern = re.compile(r'\s((?:isi_|celog|/boot)[\w./-]+)(?=\[|:)')
        level_pattern = re.compile(r'\b(DEBUG|INFO|WARN|WARNING|ERROR|FATAL|CRITICAL)\b', re.IGNORECASE)
        
        for line in lines:
            if not line.strip():
                continue
                
            try:
                # Extract timestamp
                timestamp_match = timestamp_pattern.search(line)
                timestamp = timestamp_match.group(1) if timestamp_match else None
                
                # Extract program name
                program_match = program_pattern.search(line)
                program = program_match.group(1) if program_match else None
                
                # Extract log level
                level_match = level_pattern.search(line)
                level = level_match.group(1).upper() if level_match else None
                
                # Extract message (everything after timestamp and program)
                message = line
                if timestamp_match:
                    message = line[timestamp_match.end():].strip()
                if program_match and message.startswith(program_match.group(1)):
                    message = message[len(program_match.group(1)):].strip()
                    if message.startswith('[') or message.startswith(':'):
                        # Remove process ID and colon
                        colon_idx = message.find(':')
                        if colon_idx > 0:
                            message = message[colon_idx + 1:].strip()
                
                # Insert into database
                sql = f"""
                INSERT INTO {table_name} (timestamp, program, message, level, full_line, source_file)
                VALUES (?, ?, ?, ?, ?, ?)
                """
                self.connection.execute(sql, (
                    timestamp, program, message, level, line, str(filepath)
                ))
                imported_count += 1
                
            except Exception as e:
                logging.warning(f"Failed to parse line: {line[:100]}... Error: {e}")
                failed_count += 1
                continue
        
        self.connection.commit()
        
        return {
            'table_name': table_name,
            'imported_lines': imported_count,
            'failed_lines': failed_count,
            'total_lines': len(lines),
            'source_file': str(filepath)
        }
    
    def execute_query(self, query: str, params: Optional[Tuple] = None) -> Dict[str, Any]:
        """Execute SQL query and return results."""
        try:
            # Validate query for security (basic protection)
            if not self._is_safe_query(query):
                raise ValueError("Unsafe query detected. Only SELECT statements are allowed.")
            
            cursor = self.connection.execute(query, params or ())
            
            # Get column names
            columns = [description[0] for description in cursor.description]
            
            # Fetch all results
            rows = cursor.fetchall()
            
            # Convert to list of dicts
            results = []
            for row in rows:
                results.append(dict(zip(columns, row)))
            
            return {
                'query': query,
                'columns': columns,
                'rows': results,
                'row_count': len(results)
            }
            
        except Exception as e:
            raise Exception(f"Query execution failed: {e}")
    
    def _is_safe_query(self, query: str) -> bool:
        """Basic query validation for security."""
        query_upper = query.upper().strip()
        
        # Only allow SELECT statements
        if not query_upper.startswith('SELECT'):
            return False
        
        # Block potentially dangerous keywords
        dangerous_keywords = [
            'DROP', 'DELETE', 'INSERT', 'UPDATE', 'CREATE', 'ALTER', 
            'PRAGMA', 'ATTACH', 'DETACH', 'VACUUM'
        ]
        
        for keyword in dangerous_keywords:
            if keyword in query_upper:
                return False
        
        return True
    
    def list_tables(self) -> List[str]:
        """List all tables in the database."""
        try:
            cursor = self.connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
            return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            logging.error(f"Failed to list tables: {e}")
            return []
    
    def get_table_schema(self, table_name: str) -> List[Dict[str, Any]]:
        """Get schema information for a table."""
        try:
            cursor = self.connection.execute(f"PRAGMA table_info({table_name})")
            schema = []
            for row in cursor.fetchall():
                schema.append({
                    'column_id': row[0],
                    'name': row[1],
                    'type': row[2],
                    'not_null': bool(row[3]),
                    'default_value': row[4],
                    'primary_key': bool(row[5])
                })
            return schema
        except Exception as e:
            logging.error(f"Failed to get schema for table {table_name}: {e}")
            return []
    
    def delete_table(self, table_name: str) -> bool:
        """Delete a table."""
        try:
            self.connection.execute(f"DROP TABLE IF EXISTS {table_name}")
            self.connection.commit()
            return True
        except Exception as e:
            logging.error(f"Failed to delete table {table_name}: {e}")
            return False
    
    def get_table_stats(self, table_name: str) -> Dict[str, Any]:
        """Get statistics for a table."""
        try:
            # Get row count
            cursor = self.connection.execute(f"SELECT COUNT(*) FROM {table_name}")
            row_count = cursor.fetchone()[0]
            
            # Get date range
            cursor = self.connection.execute(f"""
                SELECT MIN(timestamp), MAX(timestamp) 
                FROM {table_name} 
                WHERE timestamp IS NOT NULL
            """)
            date_range = cursor.fetchone()
            
            # Get top programs
            cursor = self.connection.execute(f"""
                SELECT program, COUNT(*) as count 
                FROM {table_name} 
                WHERE program IS NOT NULL 
                GROUP BY program 
                ORDER BY count DESC 
                LIMIT 5
            """)
            top_programs = [{'program': row[0], 'count': row[1]} for row in cursor.fetchall()]
            
            # Get log levels distribution
            cursor = self.connection.execute(f"""
                SELECT level, COUNT(*) as count 
                FROM {table_name} 
                WHERE level IS NOT NULL 
                GROUP BY level 
                ORDER BY count DESC
            """)
            log_levels = [{'level': row[0], 'count': row[1]} for row in cursor.fetchall()]
            
            return {
                'table_name': table_name,
                'row_count': row_count,
                'date_range': {
                    'start': date_range[0] if date_range[0] else None,
                    'end': date_range[1] if date_range[1] else None
                },
                'top_programs': top_programs,
                'log_levels': log_levels
            }
            
        except Exception as e:
            logging.error(f"Failed to get stats for table {table_name}: {e}")
            return {}


# Global database instance
_db_instance = None

def get_database() -> SQLLogDatabase:
    """Get or create global database instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = SQLLogDatabase()
    return _db_instance

def close_database():
    """Close global database instance."""
    global _db_instance
    if _db_instance:
        _db_instance.close()
        _db_instance = None