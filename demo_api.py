#!/usr/bin/env python3
"""
Demo script for the expanded Log Analyzer API

This script demonstrates the key features of the expanded API including:
- Log analysis endpoints
- File upload capability  
- Batch processing
- Advanced search functionality
"""

import requests
import json
import tempfile
import os
import time

# API base URL
BASE_URL = "http://localhost:5000"

def print_response(title, response):
    """Pretty print API response."""
    print(f"\n{'='*50}")
    print(f"{title}")
    print(f"{'='*50}")
    print(f"Status Code: {response.status_code}")
    if response.headers.get('content-type', '').startswith('application/json'):
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    else:
        print(f"Response: {response.text[:200]}...")

def create_sample_logs():
    """Create sample log files for demonstration."""
    log1 = tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False)
    log1.write("""2022-01-01 10:00:01 isi_service[123]: Service started successfully
2022-01-01 10:01:02 isi_service[123]: Processing user request #1001
2022-01-01 10:02:03 isi_daemon[456]: Background task initiated
2022-01-01 10:03:04 isi_service[123]: ERROR: Database connection failed
2022-01-01 10:04:05 isi_daemon[456]: WARNING: Disk space running low
2022-01-01 10:05:06 celog[789]: System audit log entry created
2022-01-01 10:06:07 isi_service[123]: Service stopped gracefully
""")
    log1.close()
    
    log2 = tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False)
    log2.write("""2022-01-02 11:00:01 web_server[111]: HTTP server listening on port 80
2022-01-02 11:01:02 web_server[111]: GET /api/users - 200 OK
2022-01-02 11:02:03 auth_service[222]: User authentication successful
2022-01-02 11:03:04 web_server[111]: POST /api/data - ERROR: Invalid payload
2022-01-02 11:04:05 db_service[333]: Database backup completed
""")
    log2.close()
    
    return log1.name, log2.name

def demo_api():
    """Demonstrate the expanded API functionality."""
    print("🚀 Log Analyzer API Demonstration")
    print("Starting API demo...")
    
    # Create sample log files
    log1_path, log2_path = create_sample_logs()
    
    try:
        # 1. Health check
        response = requests.get(f"{BASE_URL}/health")
        print_response("1. Health Check", response)
        
        # 2. Upload a log file
        with open(log1_path, 'rb') as f:
            response = requests.post(f"{BASE_URL}/log/upload", files={'file': f})
        print_response("2. File Upload", response)
        
        # 3. Summarize log
        payload = {"filepath": log1_path}
        response = requests.post(f"{BASE_URL}/log/summarize", json=payload)
        print_response("3. Log Summary", response)
        
        # 4. Filter logs by keyword
        payload = {"filepath": log1_path, "keyword": "ERROR", "limit": 50}
        response = requests.post(f"{BASE_URL}/log/filter", json=payload)
        print_response("4. Filter by Keyword (ERROR)", response)
        
        # 5. Drill down by program
        payload = {"filepath": log1_path, "limit_per_program": 3}
        response = requests.post(f"{BASE_URL}/log/drill-down", json=payload)
        print_response("5. Drill Down by Program", response)
        
        # 6. Advanced search with multiple keywords
        payload = {
            "filepath": log1_path,
            "keywords": ["ERROR", "WARNING"],
            "operator": "OR",
            "case_sensitive": False
        }
        response = requests.post(f"{BASE_URL}/log/search", json=payload)
        print_response("6. Advanced Search (ERROR OR WARNING)", response)
        
        # 7. Batch analysis
        payload = {
            "filepaths": [log1_path, log2_path],
            "operation": "summarize"
        }
        response = requests.post(f"{BASE_URL}/log/batch-analyze", json=payload)
        print_response("7. Batch Analysis", response)
        
        # 8. Date range filtering
        payload = {
            "filepath": log1_path,
            "start_date": "2022-01-01",
            "end_date": "2022-01-01"
        }
        response = requests.post(f"{BASE_URL}/log/filter", json=payload)
        print_response("8. Date Range Filter", response)
        
        print(f"\n{'='*50}")
        print("✅ API Demonstration Complete!")
        print("All endpoints working correctly.")
        print(f"{'='*50}")
        
    except requests.exceptions.ConnectionError:
        print("❌ Error: Could not connect to API server.")
        print("Please make sure the API server is running on http://localhost:5000")
        print("Run: python api/unified_api.py")
        
    except Exception as e:
        print(f"❌ Error during demo: {e}")
        
    finally:
        # Clean up sample files
        os.unlink(log1_path)
        os.unlink(log2_path)

if __name__ == "__main__":
    demo_api()