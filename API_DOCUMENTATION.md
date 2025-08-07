# Log Analyzer API Documentation

The Log Analyzer API provides SSH file browsing, log analysis, and AI-powered insights through RESTful endpoints with JWT authentication.

## Base URL
```
http://localhost:5000
```

## 🔐 Authentication

Most endpoints require JWT authentication. First, register and login to get an access token.

### Authentication Flow
1. Register: `POST /auth/register`
2. Login: `POST /auth/login` (returns JWT token)
3. Use token in header: `Authorization: Bearer <token>`

## API Overview

The API is divided into five main modules:
- **Authentication Module**: User management and JWT authentication
- **SSH Module**: For remote file browsing and downloading
- **Log Module**: For log file analysis and processing  
- **SQL Module**: For database storage and SQL querying of log data
- **AI Module**: For AI-powered log analysis and conversational interface

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
  "modules": ["ssh", "log", "sql"],
  "endpoints": {
    "ssh": [...],
    "log": [...],
    "sql": [...],
    "general": [...]
  }
}
```

## 🔐 Authentication Module Endpoints

### Register User
```
POST /auth/register
```
Register a new user account.

**Request Body:**
```json
{
  "username": "user123",
  "password": "securepassword123",
  "role": "user"  // Optional: "user" or "admin", defaults to "user"
}
```

**Response:**
```json
{
  "message": "User created successfully",
  "username": "user123",
  "role": "user"
}
```

### User Login
```
POST /auth/login
```
Authenticate user and get JWT access token.

**Request Body:**
```json
{
  "username": "user123",
  "password": "securepassword123"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "message": "Login successful",
  "user": {
    "username": "user123",
    "role": "user",
    "created_at": "2024-01-01T10:00:00"
  }
}
```

### Get User Profile
```
GET /auth/profile
Authorization: Bearer <token>
```
Get current user's profile information.

**Response:**
```json
{
  "username": "user123",
  "role": "user",
  "created_at": "2024-01-01T10:00:00"
}
```

### List Users (Admin Only)
```
GET /auth/users
Authorization: Bearer <admin_token>
```
List all users (admin role required).

**Response:**
```json
{
  "users": [
    {
      "username": "user123",
      "role": "user",
      "created_at": "2024-01-01T10:00:00"
    }
  ]
}
```

### Generate API Key
```
POST /auth/api-key
Authorization: Bearer <token>
```
Generate an API key for programmatic access.

**Response:**
```json
{
  "api_key": "ak_1234567890abcdef",
  "username": "user123",
  "message": "API key generated successfully"
}
```

### OAuth Login
```
GET /auth/oauth/<provider>
```
Initiate OAuth login with supported providers (google, github).

**Response:**
```json
{
  "auth_url": "https://accounts.google.com/o/oauth2/auth?..."
}
```

### User Logout
```
POST /auth/logout
Authorization: Bearer <token>
```
Logout user (invalidates current session).

## SSH Module Endpoints

### Connect to SSH Server
```
POST /ssh/connect
Authorization: Bearer <token>
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

## SQL Module Endpoints

### Import Log File to Database
```
POST /sql/import
```
Imports a log file into SQLite database for SQL querying.

**Request Body:**
```json
{
  "filepath": "/tmp/app.log",
  "table_name": "app_logs"
}
```

**Response:**
```json
{
  "message": "Log file imported successfully",
  "import_result": {
    "table_name": "app_logs",
    "imported_lines": 1000,
    "failed_lines": 0,
    "total_lines": 1000,
    "source_file": "/tmp/app.log"
  },
  "table_stats": {
    "table_name": "app_logs",
    "row_count": 1000,
    "date_range": {
      "start": "2023-01-01 00:00:01",
      "end": "2023-01-31 23:59:59"
    },
    "top_programs": [
      {"program": "isi_service", "count": 500}
    ],
    "log_levels": [
      {"level": "INFO", "count": 600},
      {"level": "ERROR", "count": 200}
    ]
  }
}
```

### Execute SQL Query
```
POST /sql/query
```
Executes SQL SELECT queries on imported log data.

**Request Body:**
```json
{
  "query": "SELECT level, COUNT(*) as count FROM app_logs GROUP BY level"
}
```

**Response:**
```json
{
  "message": "Query executed successfully",
  "result": {
    "query": "SELECT level, COUNT(*) as count FROM app_logs GROUP BY level",
    "columns": ["level", "count"],
    "rows": [
      {"level": "INFO", "count": 600},
      {"level": "ERROR", "count": 200}
    ],
    "row_count": 2
  }
}
```

### List Database Tables
```
GET /sql/tables
```
Lists all available tables in the database.

**Response:**
```json
{
  "tables": ["app_logs", "system_logs"],
  "table_count": 2,
  "table_details": [
    {
      "table_name": "app_logs",
      "row_count": 1000,
      "date_range": {"start": "2023-01-01", "end": "2023-01-31"},
      "top_programs": [...],
      "log_levels": [...]
    }
  ]
}
```

### Get Table Schema
```
GET /sql/schema?table=app_logs
```
Returns schema information for a specific table.

**Query Parameters:**
- `table` (required): Table name

**Response:**
```json
{
  "table_name": "app_logs",
  "schema": [
    {
      "column_id": 0,
      "name": "id",
      "type": "INTEGER",
      "not_null": false,
      "primary_key": true
    },
    {
      "column_id": 1,
      "name": "timestamp",
      "type": "TEXT",
      "not_null": false,
      "primary_key": false
    }
  ],
  "stats": {
    "row_count": 1000,
    "date_range": {...}
  }
}
```

### Delete Table
```
DELETE /sql/table
```
Deletes a table from the database.

**Request Body:**
```json
{
  "table_name": "app_logs"
}
```

**Response:**
```json
{
  "message": "Table \"app_logs\" deleted successfully"
}
```

### Upload and Import
```
POST /sql/upload-and-import
```
Uploads a log file and imports it into database in one step.

**Request:** Multipart form data
- `file`: Log file (.log or .txt extension required)
- `table_name` (optional): Custom table name

**Response:**
```json
{
  "message": "File uploaded and imported successfully",
  "uploaded_file": {
    "filename": "app.log",
    "size": 1024,
    "path": "/tmp/app.log"
  },
  "import_result": {...},
  "table_stats": {...}
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

### SQL Analysis Workflow

1. **Import log file into database:**
```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"filepath": "/tmp/app.log", "table_name": "app_logs"}' \
  http://localhost:5000/sql/import
```

2. **Query log levels distribution:**
```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"query": "SELECT level, COUNT(*) as count FROM app_logs GROUP BY level ORDER BY count DESC"}' \
  http://localhost:5000/sql/query
```

3. **Find errors from specific program:**
```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"query": "SELECT timestamp, message FROM app_logs WHERE level = \"ERROR\" AND program = \"isi_daemon\" ORDER BY timestamp"}' \
  http://localhost:5000/sql/query
```

4. **Analyze time-based patterns:**
```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"query": "SELECT substr(timestamp, 12, 2) as hour, COUNT(*) as count FROM app_logs GROUP BY hour ORDER BY hour"}' \
  http://localhost:5000/sql/query
```

5. **Upload and import in one step:**
```bash
curl -X POST -F "file=@app.log" -F "table_name=my_logs" \
  http://localhost:5000/sql/upload-and-import
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

## Database Schema

When importing logs via SQL endpoints, data is stored in the following schema:

```sql
CREATE TABLE table_name (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT,           -- Extracted timestamp (YYYY-MM-DD HH:MM:SS)
    program TEXT,            -- Program/service name (e.g., isi_service, isi_daemon)
    message TEXT,            -- Log message content
    level TEXT,              -- Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    full_line TEXT NOT NULL, -- Complete original log line
    source_file TEXT,        -- Path to source log file
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**Indexes created for performance:**
- `idx_table_timestamp` on timestamp column
- `idx_table_program` on program column  
- `idx_table_level` on level column

## Security

- **JWT Authentication**: All protected endpoints require valid JWT tokens
- **Role-Based Access**: Admin-only endpoints restrict access based on user roles
- SQL queries are restricted to SELECT statements only
- Dangerous operations (DROP, DELETE, INSERT, UPDATE) are blocked
- File uploads are limited to .log and .txt extensions
- **API Rate Limiting**: Consider implementing rate limiting in production

## 🤖 AI Module Endpoints

### AI Health Check
```
GET /ai/health
```
Check the status of AI services and available providers.

**Response:**
```json
{
  "ai_service": "healthy",
  "available_providers": ["openai", "anthropic"],
  "default_provider": "openai",
  "provider_count": 2
}
```

### List AI Providers
```
GET /ai/providers
Authorization: Bearer <token>
```
List available AI providers and their configuration status.

**Response:**
```json
{
  "available_providers": ["openai"],
  "default_provider": "openai",
  "provider_status": {
    "openai": {
      "available": true,
      "configured": true,
      "is_default": true
    },
    "anthropic": {
      "available": false,
      "configured": false,
      "is_default": false
    }
  },
  "total_available": 1
}
```

### AI Log Analysis
```
POST /ai/analyze
Authorization: Bearer <token>
```
Analyze logs using AI for intelligent insights.

**Request Body:**
```json
{
  "logs": "log content here...",  // Optional: direct log content
  "filepath": "/path/to/logfile", // Optional: file path (alternative to logs)
  "provider": "openai",           // Optional: AI provider
  "context": "Production server logs showing errors",
  "analysis_type": "error"        // Optional: error, performance, security, trend, general
}
```

**Response:**
```json
{
  "success": true,
  "analysis": "AI-generated analysis of the logs...",
  "provider": "openai",
  "analysis_type": "error",
  "timestamp": "2024-01-01T10:00:00",
  "user": "username"
}
```

### Conversational AI
```
POST /ai/chat
Authorization: Bearer <token>
```
Chat interface for natural language queries about logs.

**Request Body:**
```json
{
  "message": "What are the main issues in these logs?",
  "provider": "openai",          // Optional
  "context": ["previous", "conversation"]  // Optional
}
```

**Response:**
```json
{
  "success": true,
  "response": "AI response to your question...",
  "provider": "openai",
  "user": "username",
  "timestamp": "2024-01-01T10:00:00"
}
```

### Smart Search
```
POST /ai/smart-search
Authorization: Bearer <token>
```
Search logs using natural language descriptions.

**Request Body:**
```json
{
  "filepath": "/path/to/logfile",
  "query": "Find all security-related events and performance problems",
  "provider": "openai"           // Optional
}
```

**Response:**
```json
{
  "success": true,
  "query": "Find all security-related events and performance problems",
  "results": "AI-generated search results and analysis...",
  "provider": "openai",
  "user": "username"
}
```

### AI-Enhanced Summary
```
POST /ai/summary
Authorization: Bearer <token>
```
Generate AI-enhanced log summaries with focus areas.

**Request Body:**
```json
{
  "filepath": "/path/to/logfile",
  "provider": "openai",          // Optional
  "focus_areas": ["errors", "performance", "security"]  // Optional
}
```

**Response:**
```json
{
  "success": true,
  "traditional_summary": "Standard log summary...",
  "ai_enhanced_summary": "AI-enhanced analysis...",
  "focus_areas": ["errors", "performance", "security"],
  "provider": "openai",
  "user": "username"
}
```

## Error Responses

All endpoints may return the following error responses:

### Authentication Errors
```json
{
  "message": "Authorization token is required"
}
```
**Status Code:** 401

```json
{
  "message": "Invalid token"
}
```
**Status Code:** 401

```json
{
  "message": "Access denied. admin role required."
}
```
**Status Code:** 403

### AI Service Errors
```json
{
  "success": false,
  "message": "No LLM provider available",
  "available_providers": []
}
```
**Status Code:** 500

### General Errors
```json
{
  "message": "Request must be JSON"
}
```
**Status Code:** 400

## Configuration

### Environment Variables
Create a `.env` file with the following variables:

```bash
# Flask Configuration
FLASK_SECRET_KEY=your-secret-key
JWT_SECRET_KEY=your-jwt-secret

# AI Provider API Keys (Optional)
OPENAI_API_KEY=your-openai-key
ANTHROPIC_API_KEY=your-anthropic-key

# OAuth Configuration (Optional)
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret
```

## Getting Started Example

```bash
# 1. Register a user
curl -X POST http://localhost:5000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "testpass123"}'

# 2. Login to get token
TOKEN=$(curl -X POST http://localhost:5000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "testpass123"}' \
  | jq -r '.access_token')

# 3. Use AI analysis
curl -X POST http://localhost:5000/ai/analyze \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"logs": "2024-01-01 ERROR: Connection failed", "analysis_type": "error"}'
```
- Maximum file size: 16MB