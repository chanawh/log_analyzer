import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import tempfile
from pathlib import Path
from flask import Flask, request, jsonify, send_file, session
from werkzeug.utils import secure_filename
from core.ssh_browser import SSHBrowser
from core.log_utils import filter_log_lines, summarize_log, drill_down_by_program

app = Flask(__name__)
app.secret_key = 'supersecret'  # Needed for session management
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

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

# Health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for the entire API."""
    return jsonify({
        'status': 'healthy',
        'service': 'log_analyzer_api',
        'version': '1.0.0',
        'modules': ['ssh', 'log'],
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
            'general': [
                'GET /health'
            ]
        }
    })

# SSH API endpoints
@app.route('/ssh/connect', methods=['POST'])
def connect_ssh():
    """Connect to SSH server."""
    data = request.json
    host = data.get('host')
    username = data.get('username')
    password = data.get('password')
    if not host or not username or not password:
        return jsonify({'error': 'Missing credentials'}), 400
    browser = SSHBrowser()
    try:
        browser.connect(host, username, password)
        sid = os.urandom(16).hex()
        ssh_sessions[sid] = browser
        session['sid'] = sid
        return jsonify({'message': 'Connected', 'current_path': browser.current_path})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/ssh/list', methods=['GET'])
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

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)