# Log Analyzer API Documentation

The Log Analyzer API provides both SSH file browsing and log analysis capabilities through RESTful endpoints.

## Base URL
```
http://localhost:5000
```

## API Overview

The API is divided into two main modules:
- **SSH Module**: For remote file browsing and downloading
- **Log Module**: For log file analysis and processing

## General Endpoints

### Health Check
```
GET /health
```
Returns the API status and available endpoints.

**Response:**
```json
{
  "status": "healthy",
  "service": "log_analyzer_api", 
  "version": "1.0.0",
  "modules": ["ssh", "log"],
  "endpoints": {
    "ssh": [...],
    "log": [...],
    "general": [...]
  }
}
```

## SSH Module Endpoints

### Connect to SSH Server
```
POST /ssh/connect
```
Establishes an SSH connection to a remote server.

**Request Body:**
```json
{
  "host": "server.example.com",
  "username": "user", 
  "password": "password"
}
```

**Response:**
```json
{
  "message": "Connected",
  "current_path": "/home/user"
}
```

### List Directory Contents
```
GET /ssh/list?path=/optional/path
```
Lists files and directories on the connected SSH server.

**Query Parameters:**
- `path` (optional): Directory path to list. Defaults to current directory.

**Response:**
```json
{
  "items": [
    {"name": "file.log", "is_dir": false},
    {"name": "subdir", "is_dir": true}
  ]
}
```

### Change Directory
```
POST /ssh/change
```
Changes the current directory on the SSH server.

**Request Body:**
```json
{
  "subdir": "logs"
}
```

**Response:**
```json
{
  "current_path": "/home/user/logs"
}
```

### Download File
```
POST /ssh/download
```
Downloads a file from the SSH server.

**Request Body:**
```json
{
  "filename": "app.log"
}
```

**Response:** File download stream

### Disconnect from SSH
```
POST /ssh/disconnect
```
Closes the SSH connection.

**Response:**
```json
{
  "message": "Disconnected"
}
```

## Log Analysis Module Endpoints

### Upload Log File
```
POST /log/upload
```
Uploads a log file for analysis.

**Request:** Multipart form data with file field
- `file`: Log file (.log or .txt extension required)

**Response:**
```json
{
  "message": "File uploaded successfully",
  "filename": "app.log",
  "size": 1024,
  "path": "/tmp/app.log"
}
```

### Filter Log Lines
```
POST /log/filter
```
Filters log lines based on keywords and date ranges.

**Request Body:**
```json
{
  "filepath": "/tmp/app.log",
  "keyword": "ERROR",
  "start_date": "2022-01-01",
  "end_date": "2022-01-31", 
  "limit": 100
}
```

**Response:**
```json
{
  "total_lines": 25,
  "returned_lines": 25,
  "lines": ["2022-01-01 ERROR: Something failed", ...],
  "filters": {
    "keyword": "ERROR",
    "start_date": "2022-01-01",
    "end_date": "2022-01-31",
    "limit": 100
  }
}
```

### Summarize Log File
```
POST /log/summarize
```
Generates a statistical summary of a log file.

**Request Body:**
```json
{
  "filepath": "/tmp/app.log",
  "keyword": "ERROR",
  "start_date": "2022-01-01",
  "end_date": "2022-01-31"
}
```

**Response:**
```json
{
  "summary": "📄 Total lines: 1000\n🧠 Unique programs: 5\n🏷️ Top 5 programs:\n  • isi_service: 500 entries\n  • isi_daemon: 300 entries\n🕒 Time range: 2022-01-01 10:00:01 → 2022-01-31 23:59:59",
  "filters": {
    "keyword": "ERROR",
    "start_date": "2022-01-01", 
    "end_date": "2022-01-31"
  }
}
```

### Drill Down by Program
```
POST /log/drill-down
```
Groups log entries by program for detailed analysis.

**Request Body:**
```json
{
  "filepath": "/tmp/app.log",
  "limit_per_program": 10
}
```

**Response:**
```json
{
  "programs": {
    "isi_service": {
      "total_entries": 500,
      "entries": ["2022-01-01 isi_service[123]: Started", ...]
    },
    "isi_daemon": {
      "total_entries": 300,
      "entries": ["2022-01-01 isi_daemon[456]: Running", ...]
    }
  },
  "total_programs": 2,
  "limit_per_program": 10
}
```

## Error Responses

All endpoints return appropriate HTTP status codes and error messages:

**400 Bad Request:**
```json
{
  "error": "Missing required parameter"
}
```

**401 Unauthorized:**
```json
{
  "error": "Not connected"
}
```

**404 Not Found:**
```json
{
  "error": "File not found"
}
```

**500 Internal Server Error:**
```json
{
  "error": "Internal server error message"
}
```

## Usage Examples

### Complete Log Analysis Workflow

1. **Upload a log file:**
```bash
curl -X POST -F "file=@app.log" http://localhost:5000/log/upload
```

2. **Get summary:**
```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"filepath": "/tmp/app.log"}' \
  http://localhost:5000/log/summarize
```

3. **Filter for errors:**
```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"filepath": "/tmp/app.log", "keyword": "ERROR"}' \
  http://localhost:5000/log/filter
```

4. **Drill down by program:**
```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"filepath": "/tmp/app.log"}' \
  http://localhost:5000/log/drill-down
```

### SSH File Access Workflow

1. **Connect to server:**
```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"host": "server.com", "username": "user", "password": "pass"}' \
  http://localhost:5000/ssh/connect
```

2. **List files:**
```bash
curl -X GET http://localhost:5000/ssh/list
```

3. **Download log file:**
```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"filename": "app.log"}' \
  http://localhost:5000/ssh/download -o app.log
```

4. **Disconnect:**
```bash
curl -X POST http://localhost:5000/ssh/disconnect
```

## File Size Limits

- Maximum upload file size: 16MB
- Supported file extensions: .log, .txt
- Response line limits apply to prevent memory issues

## Session Management

SSH connections use Flask sessions for state management. Each connection gets a unique session ID that tracks the SSH browser instance.