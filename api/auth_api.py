"""
Authentication API endpoints for the Log Analyzer.

Provides JWT authentication, user management, and OAuth integration endpoints.
"""

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from flask import Flask, request, jsonify, redirect, url_for
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from flask_cors import cross_origin
import requests
import logging

from core.auth import (
    setup_auth, authenticate_user, create_user, users_db, 
    get_oauth_config, require_admin, generate_api_key
)

logger = logging.getLogger(__name__)

def register_auth_routes(app: Flask):
    """Register authentication routes with the Flask app."""
    
    @app.route('/auth/login', methods=['POST'])
    @cross_origin()
    def login():
        """Authenticate user and return JWT token."""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'message': 'Request must be JSON'}), 400
                
            username = data.get('username')
            password = data.get('password')
            
            if not username or not password:
                return jsonify({'message': 'Username and password required'}), 400
            
            user = authenticate_user(username, password)
            if user:
                access_token = create_access_token(identity=username)
                return jsonify({
                    'access_token': access_token,
                    'user': user,
                    'message': 'Login successful'
                }), 200
            else:
                return jsonify({'message': 'Invalid credentials'}), 401
                
        except Exception as e:
            logger.error(f"Login error: {e}")
            return jsonify({'message': 'Login failed', 'error': str(e)}), 500

    @app.route('/auth/register', methods=['POST'])
    @cross_origin()
    def register():
        """Register a new user."""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'message': 'Request must be JSON'}), 400
                
            username = data.get('username')
            password = data.get('password')
            role = data.get('role', 'user')
            
            if not username or not password:
                return jsonify({'message': 'Username and password required'}), 400
            
            if len(password) < 6:
                return jsonify({'message': 'Password must be at least 6 characters'}), 400
            
            if role not in ['user', 'admin']:
                role = 'user'  # Default to user role
            
            if create_user(username, password, role):
                return jsonify({
                    'message': 'User created successfully',
                    'username': username,
                    'role': role
                }), 201
            else:
                return jsonify({'message': 'Username already exists'}), 409
                
        except Exception as e:
            logger.error(f"Registration error: {e}")
            return jsonify({'message': 'Registration failed', 'error': str(e)}), 500

    @app.route('/auth/profile', methods=['GET'])
    @jwt_required()
    @cross_origin()
    def get_profile():
        """Get current user profile."""
        try:
            current_user = get_jwt_identity()
            user_data = users_db.get(current_user)
            
            if user_data:
                return jsonify({
                    'username': current_user,
                    'role': user_data['role'],
                    'created_at': user_data['created_at']
                }), 200
            else:
                return jsonify({'message': 'User not found'}), 404
                
        except Exception as e:
            logger.error(f"Profile error: {e}")
            return jsonify({'message': 'Failed to get profile', 'error': str(e)}), 500

    @app.route('/auth/users', methods=['GET'])
    @require_admin
    @cross_origin()
    def list_users():
        """List all users (admin only)."""
        try:
            users_list = []
            for username, user_data in users_db.items():
                users_list.append({
                    'username': username,
                    'role': user_data['role'],
                    'created_at': user_data['created_at']
                })
            
            return jsonify({'users': users_list}), 200
            
        except Exception as e:
            logger.error(f"List users error: {e}")
            return jsonify({'message': 'Failed to list users', 'error': str(e)}), 500

    @app.route('/auth/api-key', methods=['POST'])
    @jwt_required()
    @cross_origin()
    def generate_user_api_key():
        """Generate API key for the current user."""
        try:
            current_user = get_jwt_identity()
            api_key = generate_api_key()
            
            # In a real application, store this API key in the database
            # For now, we'll just return it
            return jsonify({
                'api_key': api_key,
                'username': current_user,
                'message': 'API key generated successfully'
            }), 200
            
        except Exception as e:
            logger.error(f"API key generation error: {e}")
            return jsonify({'message': 'Failed to generate API key', 'error': str(e)}), 500

    # OAuth endpoints (simplified implementation)
    @app.route('/auth/oauth/<provider>')
    @cross_origin()
    def oauth_login(provider):
        """Initiate OAuth login with a provider."""
        try:
            config = get_oauth_config(provider)
            if not config or not config.get('client_id'):
                return jsonify({'message': f'OAuth provider {provider} not configured'}), 400
            
            if provider == 'google':
                auth_url = (
                    f"https://accounts.google.com/o/oauth2/auth?"
                    f"client_id={config['client_id']}&"
                    f"redirect_uri={config['redirect_uri']}&"
                    f"scope=email profile&"
                    f"response_type=code"
                )
            elif provider == 'github':
                auth_url = (
                    f"https://github.com/login/oauth/authorize?"
                    f"client_id={config['client_id']}&"
                    f"redirect_uri={config['redirect_uri']}&"
                    f"scope=user:email"
                )
            else:
                return jsonify({'message': f'Unsupported OAuth provider: {provider}'}), 400
            
            return jsonify({'auth_url': auth_url}), 200
            
        except Exception as e:
            logger.error(f"OAuth login error: {e}")
            return jsonify({'message': 'OAuth login failed', 'error': str(e)}), 500

    @app.route('/auth/callback/<provider>')
    @cross_origin()
    def oauth_callback(provider):
        """Handle OAuth callback from provider."""
        try:
            code = request.args.get('code')
            if not code:
                return jsonify({'message': 'Authorization code not provided'}), 400
            
            config = get_oauth_config(provider)
            if not config:
                return jsonify({'message': f'OAuth provider {provider} not configured'}), 400
            
            # This is a simplified implementation
            # In production, you would exchange the code for an access token
            # and then fetch user information to create/authenticate the user
            
            return jsonify({
                'message': f'OAuth callback received for {provider}',
                'code': code[:10] + '...',  # Don't expose full code in response
                'provider': provider
            }), 200
            
        except Exception as e:
            logger.error(f"OAuth callback error: {e}")
            return jsonify({'message': 'OAuth callback failed', 'error': str(e)}), 500

    @app.route('/auth/logout', methods=['POST'])
    @jwt_required()
    @cross_origin()
    def logout():
        """Logout user (in a real app, you might want to blacklist the token)."""
        try:
            current_user = get_jwt_identity()
            return jsonify({
                'message': f'User {current_user} logged out successfully'
            }), 200
            
        except Exception as e:
            logger.error(f"Logout error: {e}")
            return jsonify({'message': 'Logout failed', 'error': str(e)}), 500