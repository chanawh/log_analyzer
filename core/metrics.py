"""
Prometheus metrics module for Log Analyzer application.
Provides comprehensive monitoring and observability metrics.
"""

from prometheus_client import Counter, Histogram, Gauge, generate_latest, CollectorRegistry, CONTENT_TYPE_LATEST
from functools import wraps
import time
from flask import Response

# Create a custom registry for our metrics
REGISTRY = CollectorRegistry()

# Define metrics
HTTP_REQUESTS_TOTAL = Counter(
    'log_analyzer_http_requests_total',
    'Total number of HTTP requests',
    ['method', 'endpoint', 'status_code'],
    registry=REGISTRY
)

HTTP_REQUEST_DURATION = Histogram(
    'log_analyzer_http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint'],
    registry=REGISTRY
)

HTTP_REQUEST_EXCEPTIONS = Counter(
    'log_analyzer_http_request_exceptions_total',
    'Total number of HTTP request exceptions',
    ['method', 'endpoint', 'exception_type'],
    registry=REGISTRY
)

ACTIVE_CONNECTIONS = Gauge(
    'log_analyzer_active_connections',
    'Number of active connections',
    registry=REGISTRY
)

SSH_CONNECTIONS_TOTAL = Counter(
    'log_analyzer_ssh_connections_total',
    'Total number of SSH connections',
    ['status'],
    registry=REGISTRY
)

SSH_ACTIVE_SESSIONS = Gauge(
    'log_analyzer_ssh_active_sessions',
    'Number of active SSH sessions',
    registry=REGISTRY
)

LOG_FILES_PROCESSED = Counter(
    'log_analyzer_log_files_processed_total',
    'Total number of log files processed',
    ['operation'],
    registry=REGISTRY
)

LOG_LINES_PROCESSED = Counter(
    'log_analyzer_log_lines_processed_total',
    'Total number of log lines processed',
    registry=REGISTRY
)

SQL_QUERIES_TOTAL = Counter(
    'log_analyzer_sql_queries_total',
    'Total number of SQL queries executed',
    ['status'],
    registry=REGISTRY
)

SQL_QUERY_DURATION = Histogram(
    'log_analyzer_sql_query_duration_seconds',
    'SQL query duration in seconds',
    registry=REGISTRY
)

DATABASE_SIZE_BYTES = Gauge(
    'log_analyzer_database_size_bytes',
    'Size of the database in bytes',
    registry=REGISTRY
)

UPLOAD_SIZE_BYTES = Histogram(
    'log_analyzer_upload_size_bytes',
    'Size of uploaded files in bytes',
    registry=REGISTRY
)

APPLICATION_INFO = Gauge(
    'log_analyzer_application_info',
    'Application information',
    ['version', 'python_version'],
    registry=REGISTRY
)

def setup_metrics():
    """Initialize application metrics with default values."""
    import sys
    APPLICATION_INFO.labels(
        version='1.0.0',
        python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    ).set(1)

def track_requests(f):
    """Decorator to track HTTP requests."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        start_time = time.time()
        endpoint = f.__name__
        method = 'unknown'
        
        try:
            from flask import request
            method = request.method
        except:
            pass
        
        status_code = '500'
        exception_type = None
        
        try:
            result = f(*args, **kwargs)
            if hasattr(result, 'status_code'):
                status_code = str(result.status_code)
            else:
                status_code = '200'
            return result
        except Exception as e:
            exception_type = type(e).__name__
            HTTP_REQUEST_EXCEPTIONS.labels(
                method=method,
                endpoint=endpoint,
                exception_type=exception_type
            ).inc()
            raise
        finally:
            duration = time.time() - start_time
            HTTP_REQUEST_DURATION.labels(
                method=method,
                endpoint=endpoint
            ).observe(duration)
            
            HTTP_REQUESTS_TOTAL.labels(
                method=method,
                endpoint=endpoint,
                status_code=status_code
            ).inc()
    
    return decorated_function

def track_ssh_connection(status):
    """Track SSH connection attempts."""
    SSH_CONNECTIONS_TOTAL.labels(status=status).inc()

def track_ssh_session_change(delta):
    """Track changes in SSH session count."""
    SSH_ACTIVE_SESSIONS.inc(delta)

def track_log_processing(operation, lines_count=0):
    """Track log file processing."""
    LOG_FILES_PROCESSED.labels(operation=operation).inc()
    if lines_count > 0:
        LOG_LINES_PROCESSED.inc(lines_count)

def track_sql_query(status, duration=None):
    """Track SQL query execution."""
    SQL_QUERIES_TOTAL.labels(status=status).inc()
    if duration is not None:
        SQL_QUERY_DURATION.observe(duration)

def track_upload(size_bytes):
    """Track file uploads."""
    UPLOAD_SIZE_BYTES.observe(size_bytes)

def update_database_size(size_bytes):
    """Update database size metric."""
    DATABASE_SIZE_BYTES.set(size_bytes)

def get_metrics():
    """Generate metrics in Prometheus format."""
    return Response(generate_latest(REGISTRY), mimetype=CONTENT_TYPE_LATEST)