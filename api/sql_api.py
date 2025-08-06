import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import tempfile
import logging
from pathlib import Path
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
from core.sql_utils import get_database, SQLLogDatabase

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

UPLOAD_FOLDER = tempfile.gettempdir()
ALLOWED_EXTENSIONS = {'log', 'txt'}

def allowed_file(filename):
    """Check if the uploaded file has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def sanitize_table_name(name: str) -> str:
    """Sanitize table name to be SQL-safe."""
    # Remove any non-alphanumeric characters except underscore
    import re
    sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', name)
    # Ensure it starts with a letter or underscore
    if sanitized and sanitized[0].isdigit():
        sanitized = 'table_' + sanitized
    return sanitized or 'default_table'

@app.route('/sql/import', methods=['POST'])
def import_log_file():
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
def execute_sql_query():
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
def list_tables():
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
def get_table_schema():
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
def delete_table():
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
def upload_and_import():
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
    app.run(debug=True, host='0.0.0.0', port=5001)