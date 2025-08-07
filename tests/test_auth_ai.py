"""
Tests for authentication and AI features.
"""

import sys
import os
import tempfile
import json
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import unittest
from unittest.mock import patch, MagicMock
from api.unified_api import app

class TestAuthentication(unittest.TestCase):
    """Test authentication functionality."""
    
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
    
    def test_register_user(self):
        """Test user registration."""
        payload = {
            'username': 'testuser',
            'password': 'testpass123',
            'role': 'user'
        }
        
        response = self.app.post('/auth/register',
                               data=json.dumps(payload),
                               content_type='application/json')
        
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        self.assertEqual(data['username'], 'testuser')
        self.assertEqual(data['role'], 'user')
    
    def test_login_user(self):
        """Test user login."""
        # First register a user
        register_payload = {
            'username': 'logintest',
            'password': 'testpass123'
        }
        self.app.post('/auth/register',
                     data=json.dumps(register_payload),
                     content_type='application/json')
        
        # Then login
        login_payload = {
            'username': 'logintest',
            'password': 'testpass123'
        }
        
        response = self.app.post('/auth/login',
                               data=json.dumps(login_payload),
                               content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('access_token', data)
        self.assertEqual(data['user']['username'], 'logintest')
    
    def test_invalid_login(self):
        """Test invalid login credentials."""
        payload = {
            'username': 'nonexistent',
            'password': 'wrongpass'
        }
        
        response = self.app.post('/auth/login',
                               data=json.dumps(payload),
                               content_type='application/json')
        
        self.assertEqual(response.status_code, 401)
        data = json.loads(response.data)
        self.assertEqual(data['message'], 'Invalid credentials')
    
    def test_protected_endpoint_without_token(self):
        """Test accessing protected endpoint without token."""
        response = self.app.get('/auth/profile')
        self.assertEqual(response.status_code, 401)
    
    def test_protected_endpoint_with_token(self):
        """Test accessing protected endpoint with valid token."""
        # Register and login to get token
        register_payload = {
            'username': 'tokentest',
            'password': 'testpass123'
        }
        self.app.post('/auth/register',
                     data=json.dumps(register_payload),
                     content_type='application/json')
        
        login_payload = {
            'username': 'tokentest',
            'password': 'testpass123'
        }
        login_response = self.app.post('/auth/login',
                                     data=json.dumps(login_payload),
                                     content_type='application/json')
        
        token = json.loads(login_response.data)['access_token']
        
        # Access protected endpoint
        headers = {'Authorization': f'Bearer {token}'}
        response = self.app.get('/auth/profile', headers=headers)
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['username'], 'tokentest')

class TestAIFeatures(unittest.TestCase):
    """Test AI functionality."""
    
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
        
        # Register and login to get token
        register_payload = {
            'username': 'aitest',
            'password': 'testpass123'
        }
        self.app.post('/auth/register',
                     data=json.dumps(register_payload),
                     content_type='application/json')
        
        login_payload = {
            'username': 'aitest',
            'password': 'testpass123'
        }
        login_response = self.app.post('/auth/login',
                                     data=json.dumps(login_payload),
                                     content_type='application/json')
        
        self.token = json.loads(login_response.data)['access_token']
        self.headers = {'Authorization': f'Bearer {self.token}'}
    
    def test_ai_providers_endpoint(self):
        """Test AI providers listing."""
        response = self.app.get('/ai/providers', headers=self.headers)
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertIn('available_providers', data)
        self.assertIn('provider_status', data)
    
    def test_ai_health_check(self):
        """Test AI health check."""
        response = self.app.get('/ai/health')
        self.assertIn(response.status_code, [200, 503])  # Depends on provider availability
        
        data = json.loads(response.data)
        self.assertIn('ai_service', data)
    
    @patch('core.llm_integration.llm_manager.analyze_logs_with_ai')
    def test_ai_analyze_without_provider(self, mock_analyze):
        """Test AI analysis when no provider is available."""
        mock_analyze.return_value = {
            'success': False,
            'error': 'No LLM provider available',
            'available_providers': []
        }
        
        payload = {
            'logs': 'Sample log entry with ERROR',
            'context': 'Testing AI analysis'
        }
        
        response = self.app.post('/ai/analyze',
                               data=json.dumps(payload),
                               content_type='application/json',
                               headers=self.headers)
        
        self.assertEqual(response.status_code, 500)
        data = json.loads(response.data)
        self.assertFalse(data['success'])
    
    @patch('core.llm_integration.llm_manager.analyze_logs_with_ai')
    def test_ai_analyze_with_success(self, mock_analyze):
        """Test successful AI analysis."""
        mock_analyze.return_value = {
            'success': True,
            'analysis': 'Mock AI analysis result',
            'provider': 'mock_provider',
            'timestamp': '2024-01-01T00:00:00'
        }
        
        payload = {
            'logs': 'Sample log entry with ERROR',
            'context': 'Testing AI analysis'
        }
        
        response = self.app.post('/ai/analyze',
                               data=json.dumps(payload),
                               content_type='application/json',
                               headers=self.headers)
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertEqual(data['analysis'], 'Mock AI analysis result')
    
    def test_ai_chat_missing_message(self):
        """Test AI chat with missing message."""
        payload = {}  # Empty JSON object - should be treated as invalid
        
        response = self.app.post('/ai/chat',
                               data=json.dumps(payload),
                               content_type='application/json',
                               headers=self.headers)
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        # API treats empty JSON as "no data", so it returns "Request must be JSON"
        self.assertEqual(data['message'], 'Request must be JSON')
    
    def test_ai_chat_empty_message(self):
        """Test AI chat with empty message field."""
        payload = {'message': ''}  # Empty message field
        
        response = self.app.post('/ai/chat',
                               data=json.dumps(payload),
                               content_type='application/json',
                               headers=self.headers)
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data['message'], 'Message is required')
    
    def test_ai_smart_search_missing_params(self):
        """Test AI smart search with missing parameters."""
        payload = {'query': 'test query'}  # Missing filepath
        
        response = self.app.post('/ai/smart-search',
                               data=json.dumps(payload),
                               content_type='application/json',
                               headers=self.headers)
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data['message'], 'Filepath and query are required')
    
    def test_ai_summary_missing_filepath(self):
        """Test AI summary with missing filepath."""
        payload = {}  # Empty JSON object - should be treated as invalid
        
        response = self.app.post('/ai/summary',
                               data=json.dumps(payload),
                               content_type='application/json',
                               headers=self.headers)
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        # API treats empty JSON as "no data", so it returns "Request must be JSON"
        self.assertEqual(data['message'], 'Request must be JSON')
    
    def test_ai_summary_empty_filepath(self):
        """Test AI summary with empty filepath field."""
        payload = {'filepath': ''}  # Empty filepath field
        
        response = self.app.post('/ai/summary',
                               data=json.dumps(payload),
                               content_type='application/json',
                               headers=self.headers)
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data['message'], 'Filepath is required')

class TestIntegration(unittest.TestCase):
    """Test integration between features."""
    
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
        
        # Create sample log file
        self.temp_log = tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False)
        self.temp_log.write("""2024-01-01 10:00:01 service[123]: Starting application
2024-01-01 10:00:02 service[123]: ERROR: Database connection failed
2024-01-01 10:00:03 service[123]: Retrying connection...
2024-01-01 10:00:04 service[123]: WARNING: High memory usage detected
2024-01-01 10:00:05 service[123]: Connection established successfully
""")
        self.temp_log.close()
        
        # Get authentication token
        register_payload = {
            'username': 'integrationtest',
            'password': 'testpass123'
        }
        self.app.post('/auth/register',
                     data=json.dumps(register_payload),
                     content_type='application/json')
        
        login_payload = {
            'username': 'integrationtest',
            'password': 'testpass123'
        }
        login_response = self.app.post('/auth/login',
                                     data=json.dumps(login_payload),
                                     content_type='application/json')
        
        self.token = json.loads(login_response.data)['access_token']
        self.headers = {'Authorization': f'Bearer {self.token}'}
    
    def tearDown(self):
        # Clean up temp file
        os.unlink(self.temp_log.name)
    
    @patch('core.llm_integration.llm_manager.analyze_logs_with_ai')
    def test_ai_enhanced_summary_integration(self, mock_analyze):
        """Test AI enhanced summary with file integration."""
        mock_analyze.return_value = {
            'success': True,
            'analysis': 'AI enhanced analysis of the logs',
            'provider': 'mock_provider',
            'timestamp': '2024-01-01T00:00:00'
        }
        
        payload = {
            'filepath': self.temp_log.name,
            'focus_areas': ['errors', 'performance']
        }
        
        response = self.app.post('/ai/summary',
                               data=json.dumps(payload),
                               content_type='application/json',
                               headers=self.headers)
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('traditional_summary', data)
        self.assertIn('ai_enhanced_summary', data)

if __name__ == '__main__':
    unittest.main()