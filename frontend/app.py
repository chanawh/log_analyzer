#!/usr/bin/env python3
"""
Web Frontend for Log Analyzer
Comprehensive interface to demonstrate all application features
"""

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import tempfile
import json
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file, session, flash, redirect, url_for
from werkzeug.utils import secure_filename

# Import core functionality
from core.ssh_browser import SSHBrowser
from core.log_utils import filter_log_lines, summarize_log, drill_down_by_program
from core.sql_utils import get_database, close_database
from core.metrics import setup_metrics, get_metrics

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'demo_secret_key')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Initialize metrics
setup_metrics()

# Store browser instances per session and uploaded files
ssh_sessions = {}
UPLOAD_FOLDER = tempfile.gettempdir()
ALLOWED_EXTENSIONS = {'log', 'txt'}

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

def get_browser():
    """Get the SSH browser instance for the current session."""
    sid = session.get('ssh_sid')
    if sid and sid in ssh_sessions:
        return ssh_sessions[sid]
    return None

@app.route('/')
def index():
    """Main dashboard page."""
    return render_template('index.html')

@app.route('/ssh')
def ssh_interface():
    """SSH module interface."""
    browser = get_browser()
    is_connected = browser is not None
    current_path = browser.current_path if browser else ""
    return render_template('ssh.html', is_connected=is_connected, current_path=current_path)

@app.route('/logs')
def log_interface():
    """Log analysis interface."""
    return render_template('logs.html')

@app.route('/sql')
def sql_interface():
    """SQL module interface."""
    return render_template('sql.html')

@app.route('/api/health')
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'service': 'log_analyzer_frontend',
        'version': '1.0.0',
        'modules': ['ssh', 'log', 'sql'],
        'features': {
            'ssh': 'Remote file browsing and downloading',
            'log': 'Log file analysis, filtering, and summarization',
            'sql': 'Database import and SQL querying'
        }
    })

# SSH Module API Endpoints
@app.route('/api/ssh/connect', methods=['POST'])
def ssh_connect():
    """Connect to SSH server."""
    data = request.json
    host = data.get('host', '').strip()
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    
    if not all([host, username, password]):
        return jsonify({'success': False, 'error': 'All fields are required'}), 400
    
    browser = SSHBrowser()
    try:
        browser.connect(host, username, password)
        sid = os.urandom(16).hex()
        ssh_sessions[sid] = browser
        session['ssh_sid'] = sid
        return jsonify({
            'success': True, 
            'message': 'Connected successfully',
            'current_path': browser.current_path
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/ssh/disconnect', methods=['POST'])
def ssh_disconnect():
    """Disconnect from SSH server."""
    browser = get_browser()
    if browser:
        try:
            browser.close()
            sid = session.get('ssh_sid')
            if sid:
                ssh_sessions.pop(sid, None)
            session.pop('ssh_sid', None)
            return jsonify({'success': True, 'message': 'Disconnected successfully'})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    return jsonify({'success': True, 'message': 'Already disconnected'})

@app.route('/api/ssh/list')
def ssh_list():
    """List directory contents."""
    browser = get_browser()
    if not browser:
        return jsonify({'success': False, 'error': 'Not connected'}), 401
    
    path = request.args.get('path', browser.current_path)
    try:
        items = browser.list_dir(path)
        return jsonify({
            'success': True,
            'current_path': browser.current_path,
            'items': [{'name': name, 'is_dir': is_dir} for name, is_dir in items]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/ssh/change', methods=['POST'])
def ssh_change_dir():
    """Change directory."""
    browser = get_browser()
    if not browser:
        return jsonify({'success': False, 'error': 'Not connected'}), 401
    
    data = request.json
    subdir = data.get('subdir', '').strip()
    
    try:
        browser.change_dir(subdir)
        return jsonify({
            'success': True,
            'current_path': browser.current_path
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/ssh/download', methods=['POST'])
def ssh_download():
    """Download file from SSH server."""
    browser = get_browser()
    if not browser:
        return jsonify({'success': False, 'error': 'Not connected'}), 401
    
    data = request.json
    filename = data.get('filename', '').strip()
    
    if not filename:
        return jsonify({'success': False, 'error': 'Filename is required'}), 400
    
    try:
        local_path = browser.download_file(filename)
        if local_path:
            return jsonify({
                'success': True,
                'message': f'File downloaded: {filename}',
                'local_path': local_path
            })
        else:
            return jsonify({'success': False, 'error': 'Download failed'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Log Analysis API Endpoints
@app.route('/api/log/upload', methods=['POST'])
def log_upload():
    """Upload log file."""
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected'}), 400
    
    if not file or not allowed_file(file.filename):
        return jsonify({'success': False, 'error': 'Invalid file type. Only .log and .txt files allowed'}), 400
    
    try:
        filename = secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        
        file_size = os.path.getsize(filepath)
        return jsonify({
            'success': True,
            'message': f'File uploaded: {filename}',
            'filename': filename,
            'filepath': filepath,
            'size': file_size
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/log/analyze', methods=['POST'])
def log_analyze():
    """Analyze log file with multiple operations."""
    data = request.json
    filepath = data.get('filepath', '').strip()
    operation = data.get('operation', 'summarize')
    
    if not filepath:
        return jsonify({'success': False, 'error': 'Filepath is required'}), 400
    
    log_path = Path(filepath)
    if not log_path.exists():
        return jsonify({'success': False, 'error': 'File not found'}), 404
    
    try:
        keyword_raw = data.get('keyword', '')
        keyword = keyword_raw.strip() if keyword_raw else None
        start_date_raw = data.get('start_date', '')
        start_date = start_date_raw.strip() if start_date_raw else None
        end_date_raw = data.get('end_date', '')
        end_date = end_date_raw.strip() if end_date_raw else None
        limit = data.get('limit', 100)
        
        result = {}
        
        if operation == 'summarize':
            summary = summarize_log(log_path, keyword, start_date, end_date)
            result = {'summary': summary}
            
        elif operation == 'filter':
            lines = filter_log_lines(log_path, keyword, start_date, end_date)
            limited_lines = lines[:limit] if limit else lines
            result = {
                'total_lines': len(lines),
                'returned_lines': len(limited_lines),
                'lines': limited_lines
            }
            
        elif operation == 'drill-down':
            grouped = drill_down_by_program(log_path)
            limit_per_program = data.get('limit_per_program', 10)
            limited_grouped = {}
            for program, entries in grouped.items():
                limited_grouped[program] = {
                    'total_entries': len(entries),
                    'entries': entries[:limit_per_program]
                }
            result = {
                'programs': limited_grouped,
                'total_programs': len(grouped)
            }
            
        elif operation == 'search':
            keywords_raw = data.get('keywords', [])
            if isinstance(keywords_raw, str):
                keywords = [k.strip() for k in keywords_raw.split(',') if k.strip()]
            else:
                keywords = keywords_raw
            operator = data.get('operator', 'OR')
            case_sensitive = data.get('case_sensitive', False)
            
            if not keywords:
                return jsonify({'success': False, 'error': 'Keywords are required for search'}), 400
            
            # First filter by date
            filtered_lines = filter_log_lines(log_path, None, start_date, end_date)
            
            # Apply keyword search
            matching_lines = []
            for line in filtered_lines:
                line_to_check = line if case_sensitive else line.lower()
                keywords_to_check = keywords if case_sensitive else [k.lower() for k in keywords]
                
                if operator.upper() == 'AND':
                    if all(keyword in line_to_check for keyword in keywords_to_check):
                        matching_lines.append(line)
                else:  # OR
                    if any(keyword in line_to_check for keyword in keywords_to_check):
                        matching_lines.append(line)
            
            limited_lines = matching_lines[:limit] if limit else matching_lines
            result = {
                'total_lines': len(matching_lines),
                'returned_lines': len(limited_lines),
                'lines': limited_lines,
                'search_params': {
                    'keywords': keywords,
                    'operator': operator,
                    'case_sensitive': case_sensitive
                }
            }
        else:
            return jsonify({'success': False, 'error': f'Unknown operation: {operation}'}), 400
        
        return jsonify({
            'success': True,
            'operation': operation,
            'result': result,
            'filters': {
                'keyword': keyword,
                'start_date': start_date,
                'end_date': end_date,
                'limit': limit
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# SQL Module API Endpoints
@app.route('/api/sql/import', methods=['POST'])
def sql_import():
    """Import log file into database."""
    data = request.json
    filepath = data.get('filepath', '').strip()
    table_name = data.get('table_name', '').strip()
    
    if not filepath:
        return jsonify({'success': False, 'error': 'Filepath is required'}), 400
    
    log_path = Path(filepath)
    if not log_path.exists():
        return jsonify({'success': False, 'error': 'File not found'}), 404
    
    if not table_name:
        table_name = sanitize_table_name(log_path.stem)
    else:
        table_name = sanitize_table_name(table_name)
    
    try:
        db = get_database()
        result = db.import_log_file(log_path, table_name)
        stats = db.get_table_stats(table_name)
        
        return jsonify({
            'success': True,
            'message': f'Log imported into table: {table_name}',
            'import_result': result,
            'table_stats': stats
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/sql/query', methods=['POST'])
def sql_query():
    """Execute SQL query."""
    data = request.json
    query = data.get('query', '').strip()
    
    if not query:
        return jsonify({'success': False, 'error': 'Query is required'}), 400
    
    try:
        db = get_database()
        result = db.execute_query(query)
        
        return jsonify({
            'success': True,
            'message': 'Query executed successfully',
            'result': result
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/sql/tables')
def sql_tables():
    """List all tables."""
    try:
        db = get_database()
        tables = db.list_tables()
        
        table_info = []
        for table_name in tables:
            try:
                stats = db.get_table_stats(table_name)
                table_info.append(stats)
            except:
                table_info.append({'table_name': table_name, 'error': 'Could not get stats'})
        
        return jsonify({
            'success': True,
            'tables': tables,
            'table_count': len(tables),
            'table_details': table_info
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/sql/schema')
def sql_schema():
    """Get table schema."""
    table_name = request.args.get('table', '').strip()
    
    if not table_name:
        return jsonify({'success': False, 'error': 'Table parameter is required'}), 400
    
    try:
        db = get_database()
        tables = db.list_tables()
        
        if table_name not in tables:
            return jsonify({'success': False, 'error': f'Table "{table_name}" not found'}), 404
        
        schema = db.get_table_schema(table_name)
        stats = db.get_table_stats(table_name)
        
        return jsonify({
            'success': True,
            'table_name': table_name,
            'schema': schema,
            'stats': stats
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/sql/delete-table', methods=['POST'])
def sql_delete_table():
    """Delete a table."""
    data = request.json
    table_name = data.get('table_name', '').strip()
    
    if not table_name:
        return jsonify({'success': False, 'error': 'Table name is required'}), 400
    
    try:
        db = get_database()
        tables = db.list_tables()
        
        if table_name not in tables:
            return jsonify({'success': False, 'error': f'Table "{table_name}" not found'}), 404
        
        success = db.delete_table(table_name)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Table "{table_name}" deleted successfully'
            })
        else:
            return jsonify({'success': False, 'error': f'Failed to delete table "{table_name}"'}), 500
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/metrics')
def metrics():
    """Prometheus metrics endpoint."""
    return get_metrics()

if __name__ == '__main__':
    import atexit
    atexit.register(close_database)
    app.run(debug=True, host='0.0.0.0', port=8080)