# Log Analyzer - Expanded API

A comprehensive log analysis tool with both GUI and API interfaces for analyzing log files and remote SSH file access.

## Features

### SSH Module
- Connect to remote servers via SSH
- Browse remote directories
- Download files for analysis
- Session-based connection management

### Log Analysis Module
- Upload and analyze log files
- Filter logs by keywords and date ranges
- Generate statistical summaries
- Group logs by program/service
- Advanced search with boolean operators
- Batch processing of multiple files

### API Endpoints (12 total)

**SSH Operations (5 endpoints):**
- `POST /ssh/connect` - Connect to SSH server
- `GET /ssh/list` - List directory contents
- `POST /ssh/change` - Change directory
- `POST /ssh/download` - Download files
- `POST /ssh/disconnect` - Disconnect from server

**Log Analysis (6 endpoints):**
- `POST /log/upload` - Upload log files
- `POST /log/filter` - Filter logs by keyword/date
- `POST /log/summarize` - Generate log summaries
- `POST /log/drill-down` - Group by program
- `POST /log/batch-analyze` - Batch process multiple files
- `POST /log/search` - Advanced search with boolean operators

**General (1 endpoint):**
- `GET /health` - API health check

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Start the API Server
```bash
python api/unified_api.py
```

### Run the GUI
```bash
python main.py
```

### API Demo
```bash
python demo_api.py
```

### Run Tests
```bash
python -m unittest discover tests/ -v
```

## API Documentation

See [API_DOCUMENTATION.md](API_DOCUMENTATION.md) for detailed endpoint documentation with examples.

## Files Structure

```
log_analyzer/
├── api/
│   ├── ssh_api.py        # Original SSH-only API
│   ├── log_api.py        # Log analysis API module
│   └── unified_api.py    # Combined SSH + Log API
├── core/
│   ├── log_utils.py      # Log analysis functions
│   └── ssh_browser.py    # SSH connection handling
├── gui/
│   └── gui.py           # Tkinter GUI interface
├── tests/
│   ├── test_log_utils.py # Core functionality tests
│   └── test_api.py       # API endpoint tests
├── main.py              # GUI launcher
├── demo_api.py          # API demonstration script
└── API_DOCUMENTATION.md # Complete API reference
```

## Features Added in API Expansion

- **File Upload**: Secure file upload with validation
- **Batch Processing**: Analyze multiple files simultaneously
- **Advanced Search**: Boolean operators (AND/OR) with multiple keywords
- **Error Handling**: Comprehensive validation and error responses
- **Documentation**: Complete API reference with examples
- **Testing**: Extensive test coverage for all endpoints
- **Security**: File type validation and size limits
