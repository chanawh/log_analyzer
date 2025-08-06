import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import unittest
import tempfile
import json
from pathlib import Path
from core.sql_utils import SQLLogDatabase, get_database, close_database
from api.unified_api import app as unified_app


class TestSQLUtils(unittest.TestCase):
    """Test SQL utility functions."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_db_path = tempfile.mktemp(suffix='.db')
        self.db = SQLLogDatabase(self.test_db_path)
        
        # Create test log file
        self.test_log_content = """
2023-01-01 10:00:01 isi_service[1234]: Service started successfully
2023-01-01 10:00:02 isi_daemon[5678]: ERROR: Failed to connect to database
2023-01-01 10:00:03 isi_service[1234]: INFO: Processing request
2023-01-01 10:00:04 celog[9999]: WARNING: Memory usage high
2023-01-01 10:00:05 isi_daemon[5678]: DEBUG: Connection retry attempt 1
""".strip()
        
        self.test_log_file = tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False)
        self.test_log_file.write(self.test_log_content)
        self.test_log_file.close()
    
    def tearDown(self):
        """Clean up test environment."""
        self.db.close()
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)
        if os.path.exists(self.test_log_file.name):
            os.remove(self.test_log_file.name)
    
    def test_create_table(self):
        """Test creating a table."""
        result = self.db.create_table('test_logs')
        self.assertTrue(result)
        
        tables = self.db.list_tables()
        self.assertIn('test_logs', tables)
    
    def test_import_log_file(self):
        """Test importing a log file."""
        result = self.db.import_log_file(Path(self.test_log_file.name), 'test_logs')
        
        self.assertEqual(result['table_name'], 'test_logs')
        self.assertEqual(result['imported_lines'], 5)
        self.assertEqual(result['failed_lines'], 0)
        self.assertEqual(result['total_lines'], 5)
    
    def test_execute_query(self):
        """Test executing SQL queries."""
        # Import test data
        self.db.import_log_file(Path(self.test_log_file.name), 'test_logs')
        
        # Test basic select
        result = self.db.execute_query("SELECT COUNT(*) as count FROM test_logs")
        self.assertEqual(result['row_count'], 1)
        self.assertEqual(result['rows'][0]['count'], 5)
        
        # Test filtering by program
        result = self.db.execute_query("SELECT * FROM test_logs WHERE program = 'isi_service'")
        self.assertEqual(result['row_count'], 2)
        
        # Test filtering by log level
        result = self.db.execute_query("SELECT * FROM test_logs WHERE level = 'ERROR'")
        self.assertEqual(result['row_count'], 1)
    
    def test_query_security(self):
        """Test query security validation."""
        # Import test data
        self.db.import_log_file(Path(self.test_log_file.name), 'test_logs')
        
        # Test dangerous queries are blocked
        with self.assertRaises(Exception):
            self.db.execute_query("DROP TABLE test_logs")
        
        with self.assertRaises(Exception):
            self.db.execute_query("DELETE FROM test_logs")
        
        with self.assertRaises(Exception):
            self.db.execute_query("INSERT INTO test_logs VALUES (1, 'test')")
    
    def test_get_table_schema(self):
        """Test getting table schema."""
        self.db.create_table('test_logs')
        schema = self.db.get_table_schema('test_logs')
        
        self.assertIsInstance(schema, list)
        self.assertGreater(len(schema), 0)
        
        # Check for expected columns
        column_names = [col['name'] for col in schema]
        expected_columns = ['id', 'timestamp', 'program', 'message', 'level', 'full_line', 'source_file']
        for col in expected_columns:
            self.assertIn(col, column_names)
    
    def test_get_table_stats(self):
        """Test getting table statistics."""
        # Import test data
        self.db.import_log_file(Path(self.test_log_file.name), 'test_logs')
        
        stats = self.db.get_table_stats('test_logs')
        
        self.assertEqual(stats['table_name'], 'test_logs')
        self.assertEqual(stats['row_count'], 5)
        self.assertIsNotNone(stats['date_range']['start'])
        self.assertIsNotNone(stats['date_range']['end'])
        self.assertGreater(len(stats['top_programs']), 0)
        self.assertGreater(len(stats['log_levels']), 0)
    
    def test_delete_table(self):
        """Test deleting a table."""
        self.db.create_table('test_logs')
        self.assertIn('test_logs', self.db.list_tables())
        
        result = self.db.delete_table('test_logs')
        self.assertTrue(result)
        self.assertNotIn('test_logs', self.db.list_tables())


class TestSQLAPI(unittest.TestCase):
    """Test SQL API endpoints."""
    
    def setUp(self):
        """Set up test environment."""
        self.app = unified_app.test_client()
        self.app.testing = True
        
        # Create test log file
        self.test_log_content = """
2023-01-01 10:00:01 isi_service[1234]: Service started successfully
2023-01-01 10:00:02 isi_daemon[5678]: ERROR: Failed to connect to database
2023-01-01 10:00:03 isi_service[1234]: INFO: Processing request
""".strip()
        
        self.test_log_file = tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False)
        self.test_log_file.write(self.test_log_content)
        self.test_log_file.close()
    
    def tearDown(self):
        """Clean up test environment."""
        if os.path.exists(self.test_log_file.name):
            os.remove(self.test_log_file.name)
        close_database()
    
    def test_sql_import_endpoint(self):
        """Test SQL import endpoint."""
        response = self.app.post('/sql/import', 
                                json={
                                    'filepath': self.test_log_file.name,
                                    'table_name': 'test_import'
                                })
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('message', data)
        self.assertIn('import_result', data)
        self.assertEqual(data['import_result']['table_name'], 'test_import')
    
    def test_sql_import_missing_filepath(self):
        """Test SQL import without filepath."""
        response = self.app.post('/sql/import', json={'table_name': 'test'})
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
    
    def test_sql_import_file_not_found(self):
        """Test SQL import with non-existent file."""
        response = self.app.post('/sql/import', 
                                json={
                                    'filepath': '/nonexistent/file.log',
                                    'table_name': 'test'
                                })
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertIn('error', data)
    
    def test_sql_query_endpoint(self):
        """Test SQL query endpoint."""
        # First import data
        self.app.post('/sql/import', 
                     json={
                         'filepath': self.test_log_file.name,
                         'table_name': 'test_query'
                     })
        
        # Test query
        response = self.app.post('/sql/query', 
                                json={'query': 'SELECT COUNT(*) as count FROM test_query'})
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('message', data)
        self.assertIn('result', data)
        self.assertEqual(data['result']['row_count'], 1)
    
    def test_sql_query_security(self):
        """Test SQL query security."""
        response = self.app.post('/sql/query', 
                                json={'query': 'DROP TABLE test'})
        
        self.assertEqual(response.status_code, 500)
        data = json.loads(response.data)
        self.assertIn('error', data)
    
    def test_sql_tables_endpoint(self):
        """Test SQL tables listing endpoint."""
        # Import data first
        self.app.post('/sql/import', 
                     json={
                         'filepath': self.test_log_file.name,
                         'table_name': 'test_tables'
                     })
        
        response = self.app.get('/sql/tables')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('tables', data)
        self.assertIn('table_count', data)
        self.assertIn('test_tables', data['tables'])
    
    def test_sql_schema_endpoint(self):
        """Test SQL schema endpoint."""
        # Import data first
        self.app.post('/sql/import', 
                     json={
                         'filepath': self.test_log_file.name,
                         'table_name': 'test_schema'
                     })
        
        response = self.app.get('/sql/schema?table=test_schema')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('table_name', data)
        self.assertIn('schema', data)
        self.assertIn('stats', data)
        self.assertEqual(data['table_name'], 'test_schema')
    
    def test_sql_schema_missing_table(self):
        """Test SQL schema with missing table parameter."""
        response = self.app.get('/sql/schema')
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
    
    def test_sql_schema_nonexistent_table(self):
        """Test SQL schema with nonexistent table."""
        response = self.app.get('/sql/schema?table=nonexistent')
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertIn('error', data)
    
    def test_sql_delete_table_endpoint(self):
        """Test SQL delete table endpoint."""
        # Import data first
        self.app.post('/sql/import', 
                     json={
                         'filepath': self.test_log_file.name,
                         'table_name': 'test_delete'
                     })
        
        # Delete table
        response = self.app.delete('/sql/table', 
                                  json={'table_name': 'test_delete'})
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('message', data)
        
        # Verify table is gone
        response = self.app.get('/sql/tables')
        data = json.loads(response.data)
        self.assertNotIn('test_delete', data['tables'])
    
    def test_sql_upload_and_import_endpoint(self):
        """Test SQL upload and import endpoint."""
        with open(self.test_log_file.name, 'rb') as f:
            response = self.app.post('/sql/upload-and-import',
                                   data={
                                       'file': (f, 'test.log'),
                                       'table_name': 'test_upload'
                                   })
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('message', data)
        self.assertIn('uploaded_file', data)
        self.assertIn('import_result', data)
        self.assertEqual(data['import_result']['table_name'], 'test_upload')
    
    def test_health_check_includes_sql(self):
        """Test that health check includes SQL module."""
        response = self.app.get('/health')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('sql', data['modules'])
        self.assertIn('sql', data['endpoints'])


if __name__ == '__main__':
    unittest.main()