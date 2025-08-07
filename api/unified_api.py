import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import tempfile
from pathlib import Path
from flask import Flask, request, jsonify, send_file, session
from werkzeug.utils import secure_filename
from core.ssh_browser import SSHBrowser
from core.log_utils import filter_log_lines, summarize_log, drill_down_by_program
from core.sql_utils import get_database, close_database
from core.metrics import (
    setup_metrics, track_requests, track_ssh_connection, track_ssh_session_change,
    track_log_processing, track_sql_query, track_upload, get_metrics
)

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'supersecret')  # Use environment variable
app.config['MAX_CONTENT_LENGTH'] = int(os.environ.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))

# Initialize metrics
setup_metrics()

# Store browser instances per session and uploaded files
ssh_sessions = {}
UPLOAD_FOLDER = tempfile.gettempdir()
ALLOWED_EXTENSIONS = {'log', 'txt'}

def get_browser():
    """Get the SSH browser instance for the current session."""
    sid = session.get('sid')
    if sid and sid in ssh_sessions:
        return ssh_sessions[sid]
    return None

def allowed_file(filename):
    """Check if the uploaded file has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def sanitize_table_name(name: str) -> str:
    """Sanitize table name to be SQL-safe."""
    import re
    sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', name)
    if sanitized and sanitized[0].isdigit():
        sanitized = 'table_' + sanitized
    return sanitized or 'default_table'

# Metrics endpoint
@app.route('/metrics', methods=['GET'])
def metrics():
    """Prometheus metrics endpoint."""
    return get_metrics()

# Health check endpoint
@app.route('/health', methods=['GET'])
@track_requests
def health_check():
    """Health check endpoint for the entire API."""
    return jsonify({
        'status': 'healthy',
        'service': 'log_analyzer_api',
        'version': '1.0.0',
        'modules': ['ssh', 'log', 'sql'],
        'endpoints': {
            'ssh': [
                'POST /ssh/connect',
                'GET /ssh/list',
                'POST /ssh/change',
                'POST /ssh/download',
                'POST /ssh/disconnect'
            ],
            'log': [
                'POST /log/upload',
                'POST /log/filter',
                'POST /log/summarize',
                'POST /log/drill-down',
                'POST /log/batch-analyze',
                'POST /log/search'
            ],
            'sql': [
                'POST /sql/import',
                'POST /sql/query', 
                'GET /sql/tables',
                'GET /sql/schema',
                'DELETE /sql/table',
                'POST /sql/upload-and-import'
            ],
            'general': [
                'GET /health'
            ]
        }
    })

# SSH API endpoints
@app.route('/ssh/connect', methods=['POST'])
@track_requests
def connect_ssh():
    """Connect to SSH server."""
    data = request.json
    host = data.get('host')
    username = data.get('username')
    password = data.get('password')
    if not host or not username or not password:
        track_ssh_connection('failed')
        return jsonify({'error': 'Missing credentials'}), 400
    browser = SSHBrowser()
    try:
        browser.connect(host, username, password)
        sid = os.urandom(16).hex()
        ssh_sessions[sid] = browser
        session['sid'] = sid
        track_ssh_connection('success')
        track_ssh_session_change(1)
        return jsonify({'message': 'Connected', 'current_path': browser.current_path})
    except Exception as e:
        track_ssh_connection('failed')
        return jsonify({'error': str(e)}), 500

@app.route('/ssh/list', methods=['GET'])
@track_requests
def list_dir():
    """List directory contents on SSH server."""
    browser = get_browser()
    if not browser:
        return jsonify({'error': 'Not connected'}), 401
    path = request.args.get('path', browser.current_path)
    items = browser.list_dir(path)
    return jsonify({'items': [{'name': n, 'is_dir': d} for n, d in items]})

@app.route('/ssh/change', methods=['POST'])
def change_dir():
    """Change directory on SSH server."""
    browser = get_browser()
    if not browser:
        return jsonify({'error': 'Not connected'}), 401
    data = request.json
    subdir = data.get('subdir')
    browser.change_dir(subdir)
    return jsonify({'current_path': browser.current_path})

@app.route('/ssh/download', methods=['POST'])
def download_file():
    """Download file from SSH server."""
    browser = get_browser()
    if not browser:
        return jsonify({'error': 'Not connected'}), 401
    data = request.json
    filename = data.get('filename')
    local_path = browser.download_file(filename)
    if not local_path:
        return jsonify({'error': 'Download failed'}), 500
    return send_file(local_path, as_attachment=True)

@app.route('/ssh/disconnect', methods=['POST'])
def disconnect():
    """Disconnect from SSH server."""
    browser = get_browser()
    if browser:
        browser.close()
        sid = session.get('sid')
        if sid:
            ssh_sessions.pop(sid, None)
        session.pop('sid', None)
    return jsonify({'message': 'Disconnected'})

# Log Analysis API endpoints
@app.route('/log/upload', methods=['POST'])
def upload_log_file():
    """Upload a log file for analysis."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file part in the request'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        
        # Get basic file info
        file_size = os.path.getsize(filepath)
        
        return jsonify({
            'message': 'File uploaded successfully',
            'filename': filename,
            'size': file_size,
            'path': filepath
        })
    
    return jsonify({'error': 'Invalid file type. Only .log and .txt files are allowed'}), 400

@app.route('/log/filter', methods=['POST'])
def filter_logs():
    """Filter log lines based on keyword and date range."""
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        # Get parameters
        filepath = data.get('filepath')
        keyword = data.get('keyword')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        limit = data.get('limit', 100)  # Default limit to prevent huge responses
        
        if not filepath:
            return jsonify({'error': 'filepath is required'}), 400
        
        # Convert to Path object
        log_path = Path(filepath)
        if not log_path.exists():
            return jsonify({'error': 'File not found'}), 404
        
        # Filter log lines
        filtered_lines = filter_log_lines(log_path, keyword, start_date, end_date)
        
        # Apply limit
        limited_lines = filtered_lines[:limit] if limit else filtered_lines
        
        return jsonify({
            'total_lines': len(filtered_lines),
            'returned_lines': len(limited_lines),
            'lines': limited_lines,
            'filters': {
                'keyword': keyword,
                'start_date': start_date,
                'end_date': end_date,
                'limit': limit
            }
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to filter logs: {str(e)}'}), 500

@app.route('/log/summarize', methods=['POST'])
def summarize_logs():
    """Generate a summary of the log file."""
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        # Get parameters
        filepath = data.get('filepath')
        keyword = data.get('keyword')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        if not filepath:
            return jsonify({'error': 'filepath is required'}), 400
        
        # Convert to Path object
        log_path = Path(filepath)
        if not log_path.exists():
            return jsonify({'error': 'File not found'}), 404
        
        # Generate summary
        summary = summarize_log(log_path, keyword, start_date, end_date)
        
        return jsonify({
            'summary': summary,
            'filters': {
                'keyword': keyword,
                'start_date': start_date,
                'end_date': end_date
            }
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to generate summary: {str(e)}'}), 500

@app.route('/log/drill-down', methods=['POST'])
def drill_down_logs():
    """Group log entries by program for detailed analysis."""
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        # Get parameters
        filepath = data.get('filepath')
        limit_per_program = data.get('limit_per_program', 10)
        
        if not filepath:
            return jsonify({'error': 'filepath is required'}), 400
        
        # Convert to Path object
        log_path = Path(filepath)
        if not log_path.exists():
            return jsonify({'error': 'File not found'}), 404
        
        # Group by program
        grouped_logs = drill_down_by_program(log_path)
        
        # Apply limit per program to prevent huge responses
        limited_grouped = {}
        for program, entries in grouped_logs.items():
            limited_grouped[program] = {
                'total_entries': len(entries),
                'entries': entries[:limit_per_program]
            }
        
        return jsonify({
            'programs': limited_grouped,
            'total_programs': len(grouped_logs),
            'limit_per_program': limit_per_program
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to drill down logs: {str(e)}'}), 500

@app.route('/log/batch-analyze', methods=['POST'])
def batch_analyze_logs():
    """Analyze multiple log files in batch."""
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        # Get parameters
        filepaths = data.get('filepaths', [])
        operation = data.get('operation', 'summarize')  # 'summarize', 'filter', 'drill-down'
        keyword = data.get('keyword')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        if not filepaths:
            return jsonify({'error': 'filepaths list is required'}), 400
        
        if not isinstance(filepaths, list):
            return jsonify({'error': 'filepaths must be a list'}), 400
        
        results = {}
        errors = {}
        
        for filepath in filepaths:
            try:
                log_path = Path(filepath)
                if not log_path.exists():
                    errors[filepath] = 'File not found'
                    continue
                
                if operation == 'summarize':
                    result = summarize_log(log_path, keyword, start_date, end_date)
                    results[filepath] = {'summary': result}
                elif operation == 'filter':
                    lines = filter_log_lines(log_path, keyword, start_date, end_date)
                    results[filepath] = {
                        'total_lines': len(lines),
                        'lines': lines[:50]  # Limit to 50 per file in batch
                    }
                elif operation == 'drill-down':
                    grouped = drill_down_by_program(log_path)
                    # Limit entries per program in batch mode
                    limited_grouped = {}
                    for program, entries in grouped.items():
                        limited_grouped[program] = {
                            'total_entries': len(entries),
                            'entries': entries[:5]  # Limit to 5 per program in batch
                        }
                    results[filepath] = {
                        'programs': limited_grouped,
                        'total_programs': len(grouped)
                    }
                else:
                    errors[filepath] = f'Unknown operation: {operation}'
                    
            except Exception as e:
                errors[filepath] = str(e)
        
        return jsonify({
            'operation': operation,
            'processed_files': len(results),
            'error_files': len(errors),
            'results': results,
            'errors': errors,
            'filters': {
                'keyword': keyword,
                'start_date': start_date,
                'end_date': end_date
            }
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to process batch: {str(e)}'}), 500

@app.route('/log/search', methods=['POST'])
def search_logs():
    """Advanced search with multiple keywords and boolean operators."""
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        # Get parameters
        filepath = data.get('filepath')
        keywords = data.get('keywords', [])  # List of keywords
        operator = data.get('operator', 'OR')  # 'AND' or 'OR'
        case_sensitive = data.get('case_sensitive', False)
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        limit = data.get('limit', 100)
        
        if not filepath:
            return jsonify({'error': 'filepath is required'}), 400
        
        if not keywords:
            return jsonify({'error': 'keywords list is required'}), 400
        
        # Convert to Path object
        log_path = Path(filepath)
        if not log_path.exists():
            return jsonify({'error': 'File not found'}), 404
        
        # First filter by date if provided
        filtered_lines = filter_log_lines(log_path, None, start_date, end_date)
        
        # Apply keyword search
        matching_lines = []
        for line in filtered_lines:
            line_to_check = line if case_sensitive else line.lower()
            keywords_to_check = keywords if case_sensitive else [k.lower() for k in keywords]
            
            if operator.upper() == 'AND':
                # All keywords must be present
                if all(keyword in line_to_check for keyword in keywords_to_check):
                    matching_lines.append(line)
            else:  # OR
                # At least one keyword must be present
                if any(keyword in line_to_check for keyword in keywords_to_check):
                    matching_lines.append(line)
        
        # Apply limit
        limited_lines = matching_lines[:limit] if limit else matching_lines
        
        return jsonify({
            'total_lines': len(matching_lines),
            'returned_lines': len(limited_lines),
            'lines': limited_lines,
            'search_params': {
                'keywords': keywords,
                'operator': operator,
                'case_sensitive': case_sensitive,
                'start_date': start_date,
                'end_date': end_date,
                'limit': limit
            }
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to search logs: {str(e)}'}), 500

# SQL API endpoints
@app.route('/sql/import', methods=['POST'])
def sql_import_log_file():
    """Import a log file into SQLite database."""
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        # Get parameters
        filepath = data.get('filepath')
        table_name = data.get('table_name')
        
        if not filepath:
            return jsonify({'error': 'filepath is required'}), 400
        
        if not table_name:
            # Generate table name from filename
            filename = Path(filepath).stem
            table_name = sanitize_table_name(filename)
        else:
            table_name = sanitize_table_name(table_name)
        
        # Validate file exists
        log_path = Path(filepath)
        if not log_path.exists():
            return jsonify({'error': 'File not found'}), 404
        
        # Import into database
        db = get_database()
        result = db.import_log_file(log_path, table_name)
        
        # Get table stats
        stats = db.get_table_stats(table_name)
        
        return jsonify({
            'message': 'Log file imported successfully',
            'import_result': result,
            'table_stats': stats
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to import log file: {str(e)}'}), 500

@app.route('/sql/query', methods=['POST'])
def sql_execute_query():
    """Execute SQL query on imported data."""
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        # Get parameters
        query = data.get('query')
        
        if not query:
            return jsonify({'error': 'query is required'}), 400
        
        # Execute query
        db = get_database()
        result = db.execute_query(query)
        
        return jsonify({
            'message': 'Query executed successfully',
            'result': result
        })
        
    except Exception as e:
        return jsonify({'error': f'Query execution failed: {str(e)}'}), 500

@app.route('/sql/tables', methods=['GET'])
def sql_list_tables():
    """List all available tables in the database."""
    try:
        db = get_database()
        tables = db.list_tables()
        
        # Get stats for each table
        table_info = []
        for table_name in tables:
            stats = db.get_table_stats(table_name)
            table_info.append(stats)
        
        return jsonify({
            'tables': tables,
            'table_count': len(tables),
            'table_details': table_info
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to list tables: {str(e)}'}), 500

@app.route('/sql/schema', methods=['GET'])
def sql_get_table_schema():
    """Get schema information for a table."""
    try:
        table_name = request.args.get('table')
        
        if not table_name:
            return jsonify({'error': 'table parameter is required'}), 400
        
        db = get_database()
        
        # Check if table exists
        tables = db.list_tables()
        if table_name not in tables:
            return jsonify({'error': f'Table "{table_name}" not found'}), 404
        
        # Get schema
        schema = db.get_table_schema(table_name)
        stats = db.get_table_stats(table_name)
        
        return jsonify({
            'table_name': table_name,
            'schema': schema,
            'stats': stats
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to get table schema: {str(e)}'}), 500

@app.route('/sql/table', methods=['DELETE'])
def sql_delete_table():
    """Delete a table from the database."""
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        table_name = data.get('table_name')
        
        if not table_name:
            return jsonify({'error': 'table_name is required'}), 400
        
        db = get_database()
        
        # Check if table exists
        tables = db.list_tables()
        if table_name not in tables:
            return jsonify({'error': f'Table "{table_name}" not found'}), 404
        
        # Delete table
        success = db.delete_table(table_name)
        
        if success:
            return jsonify({
                'message': f'Table "{table_name}" deleted successfully'
            })
        else:
            return jsonify({'error': f'Failed to delete table "{table_name}"'}), 500
        
    except Exception as e:
        return jsonify({'error': f'Failed to delete table: {str(e)}'}), 500

@app.route('/sql/upload-and-import', methods=['POST'])
def sql_upload_and_import():
    """Upload a log file and import it into database in one step."""
    try:
        # Check if file is in request
        if 'file' not in request.files:
            return jsonify({'error': 'No file part in the request'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not file or not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type. Only .log and .txt files are allowed'}), 400
        
        # Get optional table name from form data
        table_name = request.form.get('table_name', '')
        
        # Save uploaded file
        filename = secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        
        # Generate table name if not provided
        if not table_name:
            table_name = sanitize_table_name(Path(filename).stem)
        else:
            table_name = sanitize_table_name(table_name)
        
        # Import into database
        db = get_database()
        result = db.import_log_file(Path(filepath), table_name)
        
        # Get table stats
        stats = db.get_table_stats(table_name)
        
        return jsonify({
            'message': 'File uploaded and imported successfully',
            'uploaded_file': {
                'filename': filename,
                'size': os.path.getsize(filepath),
                'path': filepath
            },
            'import_result': result,
            'table_stats': stats
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to upload and import file: {str(e)}'}), 500

if __name__ == '__main__':
    import atexit
    atexit.register(close_database)  # Ensure database is closed on exit
    app.run(debug=True, host='0.0.0.0', port=5000)