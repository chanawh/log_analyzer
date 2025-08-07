"""
Authentication module for the Log Analyzer API.

Provides JWT authentication, OAuth integration, and user management.
"""

import os
import hashlib
import secrets
from datetime import datetime, timedelta
from functools import wraps
from flask import jsonify, request, current_app
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity
import logging

logger = logging.getLogger(__name__)

# Simple in-memory user store (in production, use a proper database)
users_db = {
    "admin": {
        "password_hash": "8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918",  # "admin"
        "role": "admin",
        "created_at": datetime.utcnow().isoformat()
    },
    "user": {
        "password_hash": "04f8996da763b7a969b1028ee3007569eaf3a635486ddab211d512c85b9df8fb",  # "user"
        "role": "user", 
        "created_at": datetime.utcnow().isoformat()
    }
}

def setup_auth(app):
    """Initialize JWT authentication for the Flask app."""
    app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'your-secret-string')
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=int(os.environ.get('JWT_EXPIRES_HOURS', 24)))
    
    jwt = JWTManager(app)
    
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({'message': 'Token has expired'}), 401
    
    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return jsonify({'message': 'Invalid token'}), 401
    
    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return jsonify({'message': 'Authorization token is required'}), 401
    
    return jwt

def hash_password(password: str) -> str:
    """Hash a password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against its hash."""
    return hash_password(password) == password_hash

def authenticate_user(username: str, password: str) -> dict:
    """Authenticate a user with username and password."""
    user = users_db.get(username)
    if user and verify_password(password, user['password_hash']):
        return {
            'username': username,
            'role': user['role'],
            'created_at': user['created_at']
        }
    return None

def create_user(username: str, password: str, role: str = 'user') -> bool:
    """Create a new user."""
    if username in users_db:
        return False
    
    users_db[username] = {
        'password_hash': hash_password(password),
        'role': role,
        'created_at': datetime.utcnow().isoformat()
    }
    return True

def require_role(role: str):
    """Decorator to require a specific role for endpoint access."""
    def decorator(f):
        @wraps(f)
        @jwt_required()
        def decorated_function(*args, **kwargs):
            current_user = get_jwt_identity()
            user_data = users_db.get(current_user)
            
            if not user_data or user_data['role'] != role:
                return jsonify({'message': f'Access denied. {role} role required.'}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def require_admin(f):
    """Decorator to require admin role."""
    return require_role('admin')(f)

def generate_api_key() -> str:
    """Generate a secure API key for service-to-service authentication."""
    return secrets.token_urlsafe(32)

# OAuth configuration (simplified - in production use proper OAuth library)
OAUTH_CONFIG = {
    'google': {
        'client_id': os.environ.get('GOOGLE_CLIENT_ID'),
        'client_secret': os.environ.get('GOOGLE_CLIENT_SECRET'),
        'redirect_uri': os.environ.get('GOOGLE_REDIRECT_URI', 'http://localhost:5000/auth/callback/google')
    },
    'github': {
        'client_id': os.environ.get('GITHUB_CLIENT_ID'), 
        'client_secret': os.environ.get('GITHUB_CLIENT_SECRET'),
        'redirect_uri': os.environ.get('GITHUB_REDIRECT_URI', 'http://localhost:5000/auth/callback/github')
    }
}

def get_oauth_config(provider: str) -> dict:
    """Get OAuth configuration for a provider."""
    return OAUTH_CONFIG.get(provider, {})