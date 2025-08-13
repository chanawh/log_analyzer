import unittest
import json
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, mock_open
import sys

# Add the parent directory to sys.path to import the API modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api.log_api import app as log_app
from api.unified_api import app as unified_app

class TestLogAPI(unittest.TestCase):
    def setUp(self):
        """Set up test client and sample data."""
        self.app = log_app.test_client()
        self.app.testing = True
        
        # Create a temporary log file for testing
        self.test_log = tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False)
        self.test_log.write(
            "2022-01-01 10:00:01 isi_service[123]: Service started\n"
            "2022-01-01 10:01:02 isi_service[123]: Processing request\n"
            "2022-01-02 11:00:03 isi_daemon[456]: Error occurred\n"
            "2022-01-02 11:01:04 celog[789]: System warning\n"
            "2022-01-03 12:00:05 isi_service[123]: Service stopped\n"
        )
        self.test_log.close()
        self.test_log_path = self.test_log.name

    def tearDown(self):
        """Clean up test files."""
        if os.path.exists(self.test_log_path):
            os.unlink(self.test_log_path)

    def test_health_check(self):
        """Test the health check endpoint."""
        response = self.app.get('/log/health')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'healthy')
        self.assertEqual(data['service'], 'log_analyzer')
        self.assertIn('endpoints', data)

    def test_filter_logs_with_keyword(self):
        """Test filtering logs with keyword."""
        payload = {
            'filepath': self.test_log_path,
            'keyword': 'Error',
            'limit': 100
        }
        response = self.app.post('/log/filter', 
                                json=payload,
                                content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['total_lines'], 1)
        self.assertIn('Error occurred', data['lines'][0])

    def test_filter_logs_with_date_range(self):
        """Test filtering logs with date range."""
        payload = {
            'filepath': self.test_log_path,
            'start_date': '2022-01-02',
            'end_date': '2022-01-02'
        }
        response = self.app.post('/log/filter',
                                json=payload,
                                content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['total_lines'], 2)  # Two entries on 2022-01-02

    def test_filter_logs_missing_filepath(self):
        """Test filtering logs without filepath."""
        payload = {'keyword': 'test'}
        response = self.app.post('/log/filter',
                                json=payload,
                                content_type='application/json')
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('filepath is required', data['error'])

    def test_filter_logs_file_not_found(self):
        """Test filtering logs with non-existent file."""
        payload = {'filepath': '/nonexistent/file.log'}
        response = self.app.post('/log/filter',
                                json=payload,
                                content_type='application/json')
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertIn('File not found', data['error'])

    def test_summarize_logs(self):
        """Test log summarization."""
        payload = {'filepath': self.test_log_path}
        response = self.app.post('/log/summarize',
                                json=payload,
                                content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('summary', data)
        self.assertIn('Total lines: 5', data['summary'])

    def test_drill_down_logs(self):
        """Test log drill-down by program."""
        payload = {
            'filepath': self.test_log_path,
            'limit_per_program': 5
        }
        response = self.app.post('/log/drill-down',
                                json=payload,
                                content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('programs', data)
        self.assertGreater(data['total_programs'], 0)
        
        # Check that isi_service entries are grouped together
        if 'isi_service' in data['programs']:
            self.assertGreater(data['programs']['isi_service']['total_entries'], 0)

    def test_upload_log_file_missing_file(self):
        """Test file upload without file."""
        response = self.app.post('/log/upload')
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('No file part', data['error'])

    def test_upload_log_file_empty_filename(self):
        """Test file upload with empty filename."""
        data = {'file': (open(self.test_log_path, 'rb'), '')}
        response = self.app.post('/log/upload', data=data)
        self.assertEqual(response.status_code, 400)
        response_data = json.loads(response.data)
        self.assertIn('No file selected', response_data['error'])

class TestUnifiedAPI(unittest.TestCase):
    def setUp(self):
        """Set up test client."""
        self.app = unified_app.test_client()
        self.app.testing = True
        
        # Create a temporary log file for testing
        self.test_log = tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False)
        self.test_log.write(
            "2022-01-01 10:00:01 isi_service[123]: Service started\n"
            "2022-01-02 11:00:03 isi_daemon[456]: Error occurred\n"
        )
        self.test_log.close()
        self.test_log_path = self.test_log.name

    def tearDown(self):
        """Clean up test files."""
        if os.path.exists(self.test_log_path):
            os.unlink(self.test_log_path)

    def test_unified_health_check(self):
        """Test the unified API health check."""
        response = self.app.get('/health')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'healthy')
        self.assertEqual(data['service'], 'log_analyzer_api')
        self.assertIn('ssh', data['endpoints'])
        self.assertIn('log', data['endpoints'])

    def test_ssh_connect_missing_credentials(self):
        """Test SSH connection without credentials."""
        payload = {'host': 'localhost'}
        response = self.app.post('/ssh/connect',
                                json=payload,
                                content_type='application/json')
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('Missing credentials', data['error'])

    def test_ssh_list_not_connected(self):
        """Test SSH list without connection."""
        response = self.app.get('/ssh/list')
        self.assertEqual(response.status_code, 401)
        data = json.loads(response.data)
        self.assertIn('Not connected', data['error'])

    def test_log_filter_in_unified_api(self):
        """Test log filtering through unified API."""
        payload = {
            'filepath': self.test_log_path,
            'keyword': 'Service'
        }
        response = self.app.post('/log/filter',
                                json=payload,
                                content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['total_lines'], 1)
        self.assertIn('Service started', data['lines'][0])

    def test_batch_analyze_logs(self):
        """Test batch analysis of multiple log files."""
        # Create a second test log file
        test_log2 = tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False)
        test_log2.write("2022-01-05 14:00:01 test_service[999]: Test message\n")
        test_log2.close()
        
        try:
            payload = {
                'filepaths': [self.test_log_path, test_log2.name],
                'operation': 'summarize'
            }
            response = self.app.post('/log/batch-analyze',
                                    json=payload,
                                    content_type='application/json')
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            self.assertEqual(data['processed_files'], 2)
            self.assertEqual(data['error_files'], 0)
            self.assertIn('results', data)
        finally:
            os.unlink(test_log2.name)

    def test_search_logs_with_multiple_keywords(self):
        """Test advanced search with multiple keywords."""
        payload = {
            'filepath': self.test_log_path,
            'keywords': ['Service', 'Error'],
            'operator': 'OR'
        }
        response = self.app.post('/log/search',
                                json=payload,
                                content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['total_lines'], 2)  # Both "Service started" and "Error occurred"

    def test_search_logs_and_operator(self):
        """Test search with AND operator."""
        payload = {
            'filepath': self.test_log_path,
            'keywords': ['2022-01-01', 'Service'],
            'operator': 'AND'
        }
        response = self.app.post('/log/search',
                                json=payload,
                                content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['total_lines'], 1)  # Only "Service started" matches both

if __name__ == '__main__':
    unittest.main()