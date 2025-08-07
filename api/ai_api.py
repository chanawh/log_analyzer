"""
AI-powered API endpoints for the Log Analyzer.

Provides LLM integration, conversational AI, and intelligent log analysis.
"""

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pathlib import Path
from flask import Flask, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_cors import cross_origin
import logging

from core.llm_integration import llm_manager, get_prompt_template
from core.log_utils import filter_log_lines, summarize_log
from core.metrics import track_log_processing

logger = logging.getLogger(__name__)

def register_ai_routes(app: Flask):
    """Register AI-powered routes with the Flask app."""
    
    @app.route('/ai/analyze', methods=['POST'])
    @jwt_required()
    @cross_origin()
    def ai_analyze_logs():
        """AI-powered log analysis using LLM."""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'message': 'Request must be JSON'}), 400
            
            logs = data.get('logs')
            filepath = data.get('filepath')
            provider = data.get('provider')  # Optional: openai, anthropic
            context = data.get('context', '')
            analysis_type = data.get('analysis_type', 'general')  # general, error, performance, security, trend
            
            if not logs and not filepath:
                return jsonify({'message': 'Either logs content or filepath must be provided'}), 400
            
            # If filepath provided, read the logs
            if filepath and not logs:
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        logs = f.read()
                except Exception as e:
                    return jsonify({'message': f'Error reading file: {str(e)}'}), 400
            
            # Limit log size for LLM processing
            max_chars = 8000  # Adjust based on model limits
            if len(logs) > max_chars:
                logs = logs[:max_chars] + "\n... (truncated for analysis)"
            
            # Add context based on analysis type
            if analysis_type != 'general':
                template = get_prompt_template(analysis_type + '_analysis')
                context = template.format(logs=logs)
                logs = ""  # Template already includes logs
            
            # Track metrics
            current_user = get_jwt_identity()
            track_log_processing('ai_analysis', len(logs.split('\n')) if logs else 0)
            
            # Perform AI analysis
            result = llm_manager.analyze_logs_with_ai(logs or context, provider, context)
            
            if result['success']:
                return jsonify({
                    'success': True,
                    'analysis': result['analysis'],
                    'provider': result['provider'],
                    'analysis_type': analysis_type,
                    'timestamp': result['timestamp'],
                    'user': current_user
                }), 200
            else:
                return jsonify({
                    'success': False,
                    'message': result['error'],
                    'available_providers': result.get('available_providers', [])
                }), 500
                
        except Exception as e:
            logger.error(f"AI analysis error: {e}")
            return jsonify({'message': 'AI analysis failed', 'error': str(e)}), 500

    @app.route('/ai/chat', methods=['POST'])
    @jwt_required()
    @cross_origin()
    def ai_chat():
        """Conversational AI interface for log-related queries."""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'message': 'Request must be JSON'}), 400
            
            message = data.get('message')
            provider = data.get('provider')
            conversation_context = data.get('context', [])  # Previous conversation
            
            if not message:
                return jsonify({'message': 'Message is required'}), 400
            
            # Get LLM provider
            llm_provider = llm_manager.get_provider(provider)
            if not llm_provider:
                available = llm_manager.list_providers()
                return jsonify({
                    'message': 'No LLM provider available',
                    'available_providers': available
                }), 400
            
            # Build conversational context
            full_prompt = f"""You are a helpful assistant specializing in log analysis and system administration.
            
Previous conversation:
{chr(10).join(conversation_context[-5:]) if conversation_context else 'None'}

User question: {message}

Please provide a helpful, accurate response related to log analysis, system troubleshooting, or related topics.
"""
            
            response = llm_provider.generate_response(full_prompt)
            
            current_user = get_jwt_identity()
            
            return jsonify({
                'success': True,
                'response': response,
                'provider': provider or llm_manager.default_provider,
                'user': current_user,
                'timestamp': llm_manager.analyze_logs_with_ai("", provider)['timestamp']
            }), 200
            
        except Exception as e:
            logger.error(f"AI chat error: {e}")
            return jsonify({'message': 'AI chat failed', 'error': str(e)}), 500

    @app.route('/ai/smart-search', methods=['POST'])
    @jwt_required()
    @cross_origin()
    def ai_smart_search():
        """Natural language search in logs using AI."""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'message': 'Request must be JSON'}), 400
            
            filepath = data.get('filepath')
            query = data.get('query')
            provider = data.get('provider')
            
            if not filepath or not query:
                return jsonify({'message': 'Filepath and query are required'}), 400
            
            # Read log file
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    logs = f.read()
            except Exception as e:
                return jsonify({'message': f'Error reading file: {str(e)}'}), 400
            
            # Get LLM provider
            llm_provider = llm_manager.get_provider(provider)
            if not llm_provider:
                available = llm_manager.list_providers()
                return jsonify({
                    'message': 'No LLM provider available',
                    'available_providers': available
                }), 400
            
            # Create smart search prompt
            search_prompt = f"""
Based on the user's natural language query, extract relevant log entries and provide analysis.

User Query: "{query}"

Log entries to search through:
{logs[:6000]}  # Limit for token constraints

Tasks:
1. Identify log entries most relevant to the query
2. Explain why these entries are relevant
3. Provide insights based on the found entries
4. Suggest any follow-up actions

Format your response with clear sections for found entries and analysis.
"""
            
            response = llm_provider.generate_response(search_prompt)
            
            current_user = get_jwt_identity()
            track_log_processing('smart_search', len(logs.split('\n')))
            
            return jsonify({
                'success': True,
                'query': query,
                'results': response,
                'provider': provider or llm_manager.default_provider,
                'user': current_user
            }), 200
            
        except Exception as e:
            logger.error(f"Smart search error: {e}")
            return jsonify({'message': 'Smart search failed', 'error': str(e)}), 500

    @app.route('/ai/summary', methods=['POST'])
    @jwt_required()
    @cross_origin()
    def ai_enhanced_summary():
        """AI-enhanced log summarization."""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'message': 'Request must be JSON'}), 400
            
            filepath = data.get('filepath')
            provider = data.get('provider')
            focus_areas = data.get('focus_areas', [])  # e.g., ['errors', 'performance', 'security']
            
            if not filepath:
                return jsonify({'message': 'Filepath is required'}), 400
            
            # Get traditional summary first
            traditional_summary = summarize_log(Path(filepath))
            
            # Read sample of logs for AI analysis
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    logs = f.read()
            except Exception as e:
                return jsonify({'message': f'Error reading file: {str(e)}'}), 400
            
            # Create focused analysis prompt
            focus_text = ", ".join(focus_areas) if focus_areas else "general analysis"
            ai_prompt = f"""
Provide an enhanced summary of these logs with focus on: {focus_text}

Traditional summary:
{traditional_summary}

Log sample for detailed analysis:
{logs[:4000]}

Please provide:
1. Executive Summary
2. Key Findings
3. Risk Assessment
4. Recommendations
5. Notable Patterns

Keep the response concise but comprehensive.
"""
            
            # Get AI analysis
            result = llm_manager.analyze_logs_with_ai(ai_prompt, provider)
            
            current_user = get_jwt_identity()
            track_log_processing('ai_summary', len(logs.split('\n')))
            
            if result['success']:
                return jsonify({
                    'success': True,
                    'traditional_summary': traditional_summary,
                    'ai_enhanced_summary': result['analysis'],
                    'focus_areas': focus_areas,
                    'provider': result['provider'],
                    'user': current_user
                }), 200
            else:
                return jsonify({
                    'success': False,
                    'traditional_summary': traditional_summary,
                    'ai_error': result['error'],
                    'available_providers': result.get('available_providers', [])
                }), 200  # Still return traditional summary
                
        except Exception as e:
            logger.error(f"AI summary error: {e}")
            return jsonify({'message': 'AI summary failed', 'error': str(e)}), 500

    @app.route('/ai/providers', methods=['GET'])
    @jwt_required()
    @cross_origin()
    def list_ai_providers():
        """List available AI providers and their status."""
        try:
            providers = llm_manager.list_providers()
            default_provider = llm_manager.default_provider
            
            provider_status = {}
            for provider in ['openai', 'anthropic']:
                api_key_env = f"{provider.upper()}_API_KEY"
                provider_status[provider] = {
                    'available': provider in providers,
                    'configured': bool(os.environ.get(api_key_env)),
                    'is_default': provider == default_provider
                }
            
            return jsonify({
                'available_providers': providers,
                'default_provider': default_provider,
                'provider_status': provider_status,
                'total_available': len(providers)
            }), 200
            
        except Exception as e:
            logger.error(f"List providers error: {e}")
            return jsonify({'message': 'Failed to list providers', 'error': str(e)}), 500

    @app.route('/ai/health', methods=['GET'])
    @cross_origin()
    def ai_health_check():
        """Health check for AI services."""
        try:
            providers = llm_manager.list_providers()
            health_status = {
                'ai_service': 'healthy' if providers else 'degraded',
                'available_providers': providers,
                'default_provider': llm_manager.default_provider,
                'provider_count': len(providers)
            }
            
            status_code = 200 if providers else 503
            return jsonify(health_status), status_code
            
        except Exception as e:
            logger.error(f"AI health check error: {e}")
            return jsonify({
                'ai_service': 'unhealthy',
                'error': str(e)
            }), 503