import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import tempfile
import json
from pathlib import Path
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
from core.log_utils import filter_log_lines, summarize_log, drill_down_by_program

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Store uploaded files temporarily
UPLOAD_FOLDER = tempfile.gettempdir()
ALLOWED_EXTENSIONS = {'log', 'txt'}

def allowed_file(filename):
    """Check if the uploaded file has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/log/health', methods=['GET'])
def health_check():
    """Health check endpoint for the log analysis API."""
    return jsonify({
        'status': 'healthy',
        'service': 'log_analyzer',
        'version': '1.0.0',
        'endpoints': [
            'GET /log/health',
            'POST /log/upload',
            'POST /log/filter',
            'POST /log/summarize',
            'POST /log/drill-down'
        ]
    })

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

if __name__ == '__main__':
    app.run(debug=True, port=5001)