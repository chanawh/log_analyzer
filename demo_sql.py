#!/usr/bin/env python3
"""
Demo script for the Log Analyzer SQL API functionality.
Shows how to use the new SQL endpoints for advanced log analysis.
"""

import requests
import json
import time
import tempfile
import os
from pathlib import Path

# Configuration
API_BASE_URL = "http://localhost:5000"
DEMO_LOG_CONTENT = """
2023-12-01 08:00:01 isi_service[1001]: INFO: Service startup initiated
2023-12-01 08:00:02 isi_daemon[2002]: DEBUG: Loading configuration from /etc/config
2023-12-01 08:00:03 isi_service[1001]: INFO: Database connection pool initialized
2023-12-01 08:00:04 celog[3003]: WARNING: Memory usage at 78% - consider cleanup
2023-12-01 08:00:05 isi_daemon[2002]: ERROR: Failed to connect to external service
2023-12-01 08:00:06 isi_service[1001]: INFO: Web server listening on port 8080
2023-12-01 08:00:07 isi_daemon[2002]: INFO: Retrying connection to external service
2023-12-01 08:00:08 /boot/loader[0001]: CRITICAL: Hardware temperature threshold exceeded
2023-12-01 08:00:09 celog[3003]: INFO: Garbage collection completed, memory freed
2023-12-01 08:00:10 isi_service[1001]: WARNING: High request volume detected
2023-12-01 08:00:11 isi_daemon[2002]: INFO: Connection to external service established
2023-12-01 08:00:12 isi_service[1001]: INFO: Request processing normalized
2023-12-01 08:00:13 celog[3003]: DEBUG: Background maintenance tasks started
2023-12-01 08:00:14 isi_daemon[2002]: INFO: All subsystems operational
2023-12-01 08:00:15 isi_service[1001]: INFO: System health check passed
""".strip()


def print_section(title):
    """Print a section header."""
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")


def print_json(data):
    """Pretty print JSON data."""
    print(json.dumps(data, indent=2))


def check_api_health():
    """Check if the API is running and includes SQL module."""
    try:
        response = requests.get(f"{API_BASE_URL}/health")
        if response.status_code == 200:
            data = response.json()
            if 'sql' in data.get('modules', []):
                print("✅ API is running with SQL module enabled")
                return True
            else:
                print("❌ API is running but SQL module not found")
                return False
        else:
            print(f"❌ API health check failed: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot connect to API: {e}")
        return False


def create_demo_log_file():
    """Create a temporary demo log file."""
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False)
    temp_file.write(DEMO_LOG_CONTENT)
    temp_file.close()
    return temp_file.name


def demo_sql_import(log_file_path):
    """Demonstrate importing a log file into the database."""
    print_section("1. SQL Import Demo")
    
    data = {
        "filepath": log_file_path,
        "table_name": "demo_logs"
    }
    
    print(f"Importing log file: {log_file_path}")
    print(f"Request: POST {API_BASE_URL}/sql/import")
    print_json(data)
    
    response = requests.post(f"{API_BASE_URL}/sql/import", json=data)
    
    if response.status_code == 200:
        result = response.json()
        print("\n✅ Import successful!")
        print_json(result)
        return True
    else:
        print(f"\n❌ Import failed: {response.status_code}")
        print(response.text)
        return False


def demo_sql_queries():
    """Demonstrate various SQL queries."""
    print_section("2. SQL Query Demos")
    
    queries = [
        {
            "name": "Count total log entries",
            "query": "SELECT COUNT(*) as total_entries FROM demo_logs"
        },
        {
            "name": "Log level distribution",
            "query": "SELECT level, COUNT(*) as count FROM demo_logs WHERE level IS NOT NULL GROUP BY level ORDER BY count DESC"
        },
        {
            "name": "Top programs by log volume",
            "query": "SELECT program, COUNT(*) as log_count FROM demo_logs WHERE program IS NOT NULL GROUP BY program ORDER BY log_count DESC"
        },
        {
            "name": "Error and warning messages",
            "query": "SELECT timestamp, program, message FROM demo_logs WHERE level IN ('ERROR', 'WARNING', 'CRITICAL') ORDER BY timestamp"
        },
        {
            "name": "Time-based analysis (by minute)",
            "query": "SELECT substr(timestamp, 1, 16) as minute, COUNT(*) as events FROM demo_logs GROUP BY minute ORDER BY minute"
        }
    ]
    
    for i, query_info in enumerate(queries, 1):
        print(f"\n--- Query {i}: {query_info['name']} ---")
        print(f"SQL: {query_info['query']}")
        
        data = {"query": query_info['query']}
        response = requests.post(f"{API_BASE_URL}/sql/query", json=data)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Query successful!")
            query_result = result['result']
            print(f"Columns: {query_result['columns']}")
            print(f"Rows returned: {query_result['row_count']}")
            
            # Print first few rows
            for row in query_result['rows'][:5]:  # Limit to 5 rows for demo
                print(f"  {row}")
            
            if query_result['row_count'] > 5:
                print(f"  ... and {query_result['row_count'] - 5} more rows")
        else:
            print(f"❌ Query failed: {response.status_code}")
            print(response.text)


def demo_table_management():
    """Demonstrate table management operations."""
    print_section("3. Table Management Demo")
    
    # List tables
    print("--- Listing all tables ---")
    response = requests.get(f"{API_BASE_URL}/sql/tables")
    if response.status_code == 200:
        result = response.json()
        print("✅ Tables listed successfully!")
        print(f"Found {result['table_count']} tables: {result['tables']}")
        
        # Show details for demo_logs table
        for table_detail in result['table_details']:
            if table_detail['table_name'] == 'demo_logs':
                print(f"\nDemo table stats:")
                print(f"  Rows: {table_detail['row_count']}")
                print(f"  Date range: {table_detail['date_range']['start']} to {table_detail['date_range']['end']}")
                print(f"  Top programs: {table_detail['top_programs']}")
                print(f"  Log levels: {table_detail['log_levels']}")
    else:
        print(f"❌ Failed to list tables: {response.status_code}")
    
    # Get schema
    print("\n--- Getting table schema ---")
    response = requests.get(f"{API_BASE_URL}/sql/schema?table=demo_logs")
    if response.status_code == 200:
        result = response.json()
        print("✅ Schema retrieved successfully!")
        print(f"Table: {result['table_name']}")
        print("Columns:")
        for col in result['schema']:
            print(f"  {col['name']} ({col['type']}) - PK: {col['primary_key']}, NOT NULL: {col['not_null']}")
    else:
        print(f"❌ Failed to get schema: {response.status_code}")


def demo_upload_and_import():
    """Demonstrate the upload and import endpoint."""
    print_section("4. Upload and Import Demo")
    
    # Create another demo file
    demo_content = """
2023-12-01 09:00:01 web_server[5001]: INFO: HTTP server started on port 80
2023-12-01 09:00:02 web_server[5001]: INFO: SSL certificate loaded successfully
2023-12-01 09:00:03 database[6001]: ERROR: Connection pool exhausted
2023-12-01 09:00:04 web_server[5001]: WARNING: High connection rate detected
2023-12-01 09:00:05 database[6001]: INFO: Connection pool expanded
""".strip()
    
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False)
    temp_file.write(demo_content)
    temp_file.close()
    
    print(f"Uploading and importing file: {temp_file.name}")
    
    try:
        with open(temp_file.name, 'rb') as f:
            files = {'file': (os.path.basename(temp_file.name), f, 'text/plain')}
            data = {'table_name': 'upload_demo'}
            
            response = requests.post(f"{API_BASE_URL}/sql/upload-and-import", 
                                   files=files, data=data)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Upload and import successful!")
            print_json(result)
        else:
            print(f"❌ Upload and import failed: {response.status_code}")
            print(response.text)
            
    finally:
        os.unlink(temp_file.name)


def demo_security():
    """Demonstrate SQL security features."""
    print_section("5. Security Demo")
    
    dangerous_queries = [
        "DROP TABLE demo_logs",
        "DELETE FROM demo_logs",
        "INSERT INTO demo_logs VALUES (1, 'test')",
        "UPDATE demo_logs SET message = 'hacked'"
    ]
    
    for query in dangerous_queries:
        print(f"\n--- Testing dangerous query: {query} ---")
        data = {"query": query}
        response = requests.post(f"{API_BASE_URL}/sql/query", json=data)
        
        if response.status_code == 500:
            result = response.json()
            if "Unsafe query" in result.get('error', ''):
                print("✅ Security working - dangerous query blocked!")
            else:
                print(f"❌ Query failed for other reason: {result}")
        else:
            print(f"⚠️  Unexpected response: {response.status_code}")


def cleanup_demo_table():
    """Clean up the demo table."""
    print_section("6. Cleanup")
    
    data = {"table_name": "demo_logs"}
    response = requests.delete(f"{API_BASE_URL}/sql/table", json=data)
    
    if response.status_code == 200:
        print("✅ Demo table deleted successfully!")
    else:
        print(f"❌ Failed to delete demo table: {response.status_code}")
    
    # Also try to cleanup upload_demo table
    data = {"table_name": "upload_demo"}
    response = requests.delete(f"{API_BASE_URL}/sql/table", json=data)
    
    if response.status_code == 200:
        print("✅ Upload demo table deleted successfully!")


def main():
    """Run the complete SQL API demo."""
    print("Log Analyzer SQL API Demo")
    print("=" * 60)
    
    # Check API health
    if not check_api_health():
        print("\n❌ Cannot proceed - API not available or SQL module missing")
        print("Please start the API server with: python api/unified_api.py")
        return
    
    # Create demo log file
    log_file = create_demo_log_file()
    
    try:
        # Run demos
        if demo_sql_import(log_file):
            demo_sql_queries()
            demo_table_management()
            demo_upload_and_import()
            demo_security()
            cleanup_demo_table()
        
        print_section("Demo Complete")
        print("✅ SQL API demo completed successfully!")
        print("\nKey capabilities demonstrated:")
        print("• Import log files into SQLite database")
        print("• Execute complex SQL queries for analysis")
        print("• Table management and schema inspection")
        print("• File upload with immediate import")
        print("• Security protection against dangerous queries")
        
    finally:
        # Cleanup demo file
        if os.path.exists(log_file):
            os.unlink(log_file)


if __name__ == "__main__":
    main()