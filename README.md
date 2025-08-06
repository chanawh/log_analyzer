# Log Analyzer - Expanded API

[![CI/CD Pipeline](https://github.com/chanawh/log_analyzer/actions/workflows/ci.yml/badge.svg)](https://github.com/chanawh/log_analyzer/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/chanawh/log_analyzer/branch/main/graph/badge.svg)](https://codecov.io/gh/chanawh/log_analyzer)

A comprehensive log analysis tool with both GUI and API interfaces for analyzing log files and remote SSH file access.

## Features

### SSH Module
- Connect to remote servers via SSH
- Browse remote directories
- Download files for analysis
- Session-based connection management

### SQL Module
- Import log files into SQLite database
- Execute SQL queries on imported data
- Database table management (create, list, delete)
- Advanced analytics with SQL aggregations
- Secure query execution (SELECT only)
- Upload and analyze log files
- Filter logs by keywords and date ranges
- Generate statistical summaries
- Group logs by program/service
- Advanced search with boolean operators
- Batch processing of multiple files

### API Endpoints (18 total)

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

**SQL Operations (6 endpoints):**
- `POST /sql/import` - Import log file to database
- `POST /sql/query` - Execute SQL queries on data
- `GET /sql/tables` - List database tables
- `GET /sql/schema` - Get table schema information
- `DELETE /sql/table` - Delete database table
- `POST /sql/upload-and-import` - Upload and import in one step

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
- **SQL Database Storage**: Import logs into SQLite for complex querying
- **SQL Query Engine**: Execute SELECT queries on imported log data
- **Database Management**: Create, list, delete tables with schema inspection
- **Error Handling**: Comprehensive validation and error responses
- **Documentation**: Complete API reference with examples
- **Testing**: Extensive test coverage for all endpoints
- **Security**: File type validation, size limits, and SQL injection protection

## CI/CD

This project includes a comprehensive CI/CD pipeline that:

- **Automated Testing**: Runs on Python 3.8-3.12 for compatibility
- **Code Quality**: Linting with flake8 for code standards
- **Test Coverage**: Coverage reporting with Codecov integration
- **Docker Support**: Containerized deployment ready
- **Multi-branch**: Supports main and develop branches

### CI/CD Features

- ✅ **Automated Tests**: Full test suite runs on every push/PR
- ✅ **Code Linting**: flake8 ensures code quality
- ✅ **Coverage Reports**: Track test coverage over time
- ✅ **Docker Building**: Container image built and tested
- ✅ **Multi-Python**: Tests against 5 Python versions
- ✅ **Caching**: Optimized builds with dependency caching

### Running Locally

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run linting
flake8 .

# Run tests with coverage
coverage run -m unittest discover tests/ -v
coverage report -m

# Build Docker image
docker build -t log-analyzer:latest .
```
