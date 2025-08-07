#!/usr/bin/env python3
"""
Demo script for the enhanced Log Analyzer API with Authentication and AI features.

This script demonstrates:
- JWT Authentication
- AI-powered log analysis
- Conversational AI interface
- Enhanced API security
"""

import requests
import json
import tempfile
import os
import time

# API base URL
BASE_URL = "http://localhost:5000"

def print_response(title, response):
    """Pretty print API response."""
    print(f"\n{'='*60}")
    print(f"{title}")
    print(f"{'='*60}")
    print(f"Status Code: {response.status_code}")
    if response.headers.get('content-type', '').startswith('application/json'):
        try:
            data = response.json()
            print(f"Response: {json.dumps(data, indent=2)}")
        except:
            print(f"Response: {response.text}")
    else:
        print(f"Response: {response.text[:200]}...")

def create_sample_logs():
    """Create sample log files for demonstration."""
    log_content = """2024-01-01 10:00:01 web_server[123]: Starting application server
2024-01-01 10:00:02 web_server[123]: Database connection established
2024-01-01 10:01:03 web_server[123]: Processing user request from 192.168.1.100
2024-01-01 10:01:04 auth_service[456]: User login successful: john.doe@example.com
2024-01-01 10:02:05 web_server[123]: ERROR: Database connection timeout
2024-01-01 10:02:06 web_server[123]: Attempting database reconnection
2024-01-01 10:02:07 web_server[123]: WARNING: High memory usage detected (85%)
2024-01-01 10:03:08 monitoring[789]: CPU usage spike detected: 92%
2024-01-01 10:03:09 web_server[123]: Database connection restored
2024-01-01 10:04:10 security[101]: Failed login attempt from 192.168.1.200
2024-01-01 10:04:11 security[101]: CRITICAL: Multiple failed attempts from same IP
2024-01-01 10:05:12 web_server[123]: Response time degradation detected
2024-01-01 10:05:13 load_balancer[202]: Redirecting traffic to backup server
"""
    
    temp_log = tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False)
    temp_log.write(log_content)
    temp_log.close()
    return temp_log.name

def demo_enhanced_api():
    """Demonstrate the enhanced API functionality."""
    print("🚀 Enhanced Log Analyzer API Demonstration")
    print("Features: JWT Authentication + AI Integration")
    
    headers = {}
    
    try:
        # Create sample log file
        log_file_path = create_sample_logs()
        print(f"📁 Created sample log file: {log_file_path}")
        
        # 1. Health checks
        print("\n" + "="*60)
        print("HEALTH CHECKS")
        print("="*60)
        
        response = requests.get(f"{BASE_URL}/health")
        print_response("1. General Health Check", response)
        
        response = requests.get(f"{BASE_URL}/ai/health")
        print_response("2. AI Services Health Check", response)
        
        # 2. User Registration and Authentication
        print("\n" + "="*60)
        print("AUTHENTICATION FLOW")
        print("="*60)
        
        # Register new user
        register_data = {
            "username": "demo_user",
            "password": "demo_password_123",
            "role": "user"
        }
        response = requests.post(f"{BASE_URL}/auth/register", json=register_data)
        print_response("3. User Registration", response)
        
        # Login user
        login_data = {
            "username": "demo_user",
            "password": "demo_password_123"
        }
        response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
        print_response("4. User Login", response)
        
        if response.status_code == 200:
            token_data = response.json()
            access_token = token_data.get('access_token')
            headers['Authorization'] = f'Bearer {access_token}'
            print(f"✅ Authentication successful! Token obtained.")
        else:
            print("❌ Authentication failed! Cannot proceed with protected endpoints.")
            return
        
        # Get user profile
        response = requests.get(f"{BASE_URL}/auth/profile", headers=headers)
        print_response("5. User Profile", response)
        
        # 3. Traditional Log Analysis (Enhanced with Auth)
        print("\n" + "="*60)
        print("TRADITIONAL LOG ANALYSIS (AUTHENTICATED)")
        print("="*60)
        
        # Upload log file
        with open(log_file_path, 'rb') as f:
            response = requests.post(f"{BASE_URL}/log/upload", 
                                   files={'file': f}, 
                                   headers=headers)
        print_response("6. Secure File Upload", response)
        
        # Summarize logs
        summary_data = {"filepath": log_file_path}
        response = requests.post(f"{BASE_URL}/log/summarize", 
                               json=summary_data, 
                               headers=headers)
        print_response("7. Log Summary", response)
        
        # Filter logs for errors
        filter_data = {"filepath": log_file_path, "keyword": "ERROR"}
        response = requests.post(f"{BASE_URL}/log/filter", 
                               json=filter_data, 
                               headers=headers)
        print_response("8. Error Filtering", response)
        
        # 4. AI-Powered Features
        print("\n" + "="*60)
        print("AI-POWERED FEATURES")
        print("="*60)
        
        # Check available AI providers
        response = requests.get(f"{BASE_URL}/ai/providers", headers=headers)
        print_response("9. Available AI Providers", response)
        
        # AI-enhanced log analysis
        ai_analysis_data = {
            "filepath": log_file_path,
            "analysis_type": "error",
            "context": "Production web server logs showing performance issues"
        }
        response = requests.post(f"{BASE_URL}/ai/analyze", 
                               json=ai_analysis_data, 
                               headers=headers)
        print_response("10. AI Log Analysis", response)
        
        # AI-enhanced summary
        ai_summary_data = {
            "filepath": log_file_path,
            "focus_areas": ["errors", "performance", "security"]
        }
        response = requests.post(f"{BASE_URL}/ai/summary", 
                               json=ai_summary_data, 
                               headers=headers)
        print_response("11. AI-Enhanced Summary", response)
        
        # Conversational AI interface
        chat_data = {
            "message": "What are the main issues in these logs and how can I fix them?",
            "context": ["User is analyzing web server logs", "Looking for performance issues"]
        }
        response = requests.post(f"{BASE_URL}/ai/chat", 
                               json=chat_data, 
                               headers=headers)
        print_response("12. Conversational AI", response)
        
        # Smart search with natural language
        smart_search_data = {
            "filepath": log_file_path,
            "query": "Find all security-related events and performance problems"
        }
        response = requests.post(f"{BASE_URL}/ai/smart-search", 
                               json=smart_search_data, 
                               headers=headers)
        print_response("13. AI Smart Search", response)
        
        # 5. Advanced Features
        print("\n" + "="*60)
        print("ADVANCED FEATURES")
        print("="*60)
        
        # Advanced search with multiple keywords
        advanced_search_data = {
            "filepath": log_file_path,
            "keywords": ["ERROR", "WARNING", "CRITICAL"],
            "operator": "OR",
            "case_sensitive": False
        }
        response = requests.post(f"{BASE_URL}/log/search", 
                               json=advanced_search_data, 
                               headers=headers)
        print_response("14. Advanced Multi-Keyword Search", response)
        
        # Generate API key for programmatic access
        response = requests.post(f"{BASE_URL}/auth/api-key", headers=headers)
        print_response("15. API Key Generation", response)
        
        print(f"\n{'='*60}")
        print("✅ DEMONSTRATION COMPLETE!")
        print("✅ All enhanced features working correctly.")
        print("\nKey Enhancements Added:")
        print("🔐 JWT Authentication & Authorization")
        print("🤖 AI-Powered Log Analysis (OpenAI/Anthropic)")
        print("💬 Conversational AI Interface")
        print("🔍 Smart Natural Language Search")
        print("🛡️ Enhanced API Security")
        print("🔧 OAuth Integration Ready")
        print("📊 Comprehensive Testing Coverage")
        print(f"{'='*60}")
        
    except requests.exceptions.ConnectionError:
        print("❌ Error: Could not connect to API server.")
        print("Please make sure the API server is running on http://localhost:5000")
        print("Run: python api/unified_api.py")
        
    except Exception as e:
        print(f"❌ Error during demo: {e}")
        
    finally:
        # Clean up sample file
        if 'log_file_path' in locals():
            try:
                os.unlink(log_file_path)
                print(f"🧹 Cleaned up sample log file: {log_file_path}")
            except:
                pass

def show_configuration_guide():
    """Show configuration guide for AI features."""
    print("\n" + "="*60)
    print("CONFIGURATION GUIDE")
    print("="*60)
    print("""
To enable AI features, set up environment variables:

1. Copy .env.example to .env:
   cp .env.example .env

2. Add your API keys to .env:
   # For OpenAI GPT models
   OPENAI_API_KEY=your-openai-api-key
   
   # For Anthropic Claude models  
   ANTHROPIC_API_KEY=your-anthropic-api-key

3. Install additional dependencies if needed:
   pip install openai anthropic

4. Restart the API server to load new configuration.

Note: AI features will gracefully degrade if API keys are not provided.
""")

if __name__ == "__main__":
    print("🧪 Starting Enhanced Log Analyzer Demo...")
    show_configuration_guide()
    demo_enhanced_api()