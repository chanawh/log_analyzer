"""
LLM Integration module for the Log Analyzer.

Provides integration with OpenAI, Anthropic, and other LLM providers
for intelligent log analysis and conversational AI capabilities.
"""

import os
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime
import json

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

logger = logging.getLogger(__name__)

class LLMProvider:
    """Base class for LLM providers."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        
    def analyze_logs(self, logs: str, context: str = "") -> str:
        """Analyze logs using the LLM."""
        raise NotImplementedError
        
    def generate_response(self, prompt: str) -> str:
        """Generate a response to a prompt."""
        raise NotImplementedError

class OpenAIProvider(LLMProvider):
    """OpenAI provider for GPT models."""
    
    def __init__(self, api_key: str, model: str = "gpt-3.5-turbo"):
        super().__init__(api_key)
        self.model = model
        if OPENAI_AVAILABLE:
            openai.api_key = api_key
        
    def analyze_logs(self, logs: str, context: str = "") -> str:
        """Analyze logs using OpenAI GPT."""
        if not OPENAI_AVAILABLE:
            return "OpenAI library not available. Please install with: pip install openai"
            
        try:
            prompt = self._create_log_analysis_prompt(logs, context)
            
            response = openai.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert system administrator and log analyst."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.3
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return f"Error analyzing logs with OpenAI: {e}"
    
    def generate_response(self, prompt: str) -> str:
        """Generate a response using OpenAI."""
        if not OPENAI_AVAILABLE:
            return "OpenAI library not available."
            
        try:
            response = openai.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return f"Error generating response: {e}"
    
    def _create_log_analysis_prompt(self, logs: str, context: str = "") -> str:
        """Create a structured prompt for log analysis."""
        base_prompt = f"""
Analyze the following log entries and provide insights:

{context and f"Context: {context}" or ""}

Log entries:
{logs}

Please provide:
1. Summary of what happened
2. Any errors or warnings identified
3. Potential issues or concerns
4. Recommendations for next steps
5. Pattern analysis if applicable

Format your response in a clear, structured manner.
"""
        return base_prompt

class AnthropicProvider(LLMProvider):
    """Anthropic Claude provider."""
    
    def __init__(self, api_key: str, model: str = "claude-3-sonnet-20240229"):
        super().__init__(api_key)
        self.model = model
        if ANTHROPIC_AVAILABLE:
            self.client = anthropic.Anthropic(api_key=api_key)
    
    def analyze_logs(self, logs: str, context: str = "") -> str:
        """Analyze logs using Anthropic Claude."""
        if not ANTHROPIC_AVAILABLE:
            return "Anthropic library not available. Please install with: pip install anthropic"
            
        try:
            prompt = self._create_log_analysis_prompt(logs, context)
            
            message = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                temperature=0.3,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            return message.content[0].text
            
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            return f"Error analyzing logs with Anthropic: {e}"
    
    def generate_response(self, prompt: str) -> str:
        """Generate a response using Anthropic Claude."""
        if not ANTHROPIC_AVAILABLE:
            return "Anthropic library not available."
            
        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=500,
                temperature=0.7,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            return message.content[0].text
            
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            return f"Error generating response: {e}"
    
    def _create_log_analysis_prompt(self, logs: str, context: str = "") -> str:
        """Create a structured prompt for log analysis."""
        base_prompt = f"""
As an expert system administrator, analyze these log entries:

{context and f"Additional context: {context}" or ""}

Log data:
{logs}

Provide a comprehensive analysis including:
1. Executive summary
2. Critical issues found
3. Warning signs
4. Performance indicators
5. Security considerations
6. Actionable recommendations

Structure your response clearly with headings.
"""
        return base_prompt

class LLMManager:
    """Manager for multiple LLM providers."""
    
    def __init__(self):
        self.providers = {}
        self.default_provider = None
        self._setup_providers()
    
    def _setup_providers(self):
        """Setup available LLM providers based on configuration."""
        # OpenAI setup
        openai_key = os.environ.get('OPENAI_API_KEY')
        if openai_key and OPENAI_AVAILABLE:
            self.providers['openai'] = OpenAIProvider(openai_key)
            if not self.default_provider:
                self.default_provider = 'openai'
                
        # Anthropic setup
        anthropic_key = os.environ.get('ANTHROPIC_API_KEY')
        if anthropic_key and ANTHROPIC_AVAILABLE:
            self.providers['anthropic'] = AnthropicProvider(anthropic_key)
            if not self.default_provider:
                self.default_provider = 'anthropic'
    
    def get_provider(self, provider_name: str = None) -> Optional[LLMProvider]:
        """Get a specific provider or the default one."""
        if provider_name:
            return self.providers.get(provider_name)
        elif self.default_provider:
            return self.providers.get(self.default_provider)
        return None
    
    def list_providers(self) -> List[str]:
        """List available providers."""
        return list(self.providers.keys())
    
    def analyze_logs_with_ai(self, logs: str, provider: str = None, context: str = "") -> Dict[str, Any]:
        """Analyze logs using AI with the specified or default provider."""
        llm_provider = self.get_provider(provider)
        
        if not llm_provider:
            available = self.list_providers()
            return {
                'success': False,
                'error': f'No LLM provider available. Available providers: {available}',
                'available_providers': available
            }
        
        try:
            analysis = llm_provider.analyze_logs(logs, context)
            return {
                'success': True,
                'analysis': analysis,
                'provider': provider or self.default_provider,
                'timestamp': datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"LLM analysis error: {e}")
            return {
                'success': False,
                'error': str(e),
                'provider': provider or self.default_provider
            }

# Prompt engineering templates
PROMPT_TEMPLATES = {
    'error_analysis': """
    Analyze the following error logs and identify:
    1. Root cause analysis
    2. Impact assessment  
    3. Recovery steps
    4. Prevention measures
    
    Logs:
    {logs}
    """,
    
    'performance_analysis': """
    Analyze these performance-related logs for:
    1. Performance bottlenecks
    2. Resource utilization patterns
    3. Optimization opportunities
    4. Capacity planning insights
    
    Logs:
    {logs}
    """,
    
    'security_analysis': """
    Review these logs for security concerns:
    1. Potential security threats
    2. Anomalous behavior
    3. Access pattern analysis
    4. Security recommendations
    
    Logs:
    {logs}
    """,
    
    'trend_analysis': """
    Analyze these logs for trends and patterns:
    1. Temporal patterns
    2. Frequency analysis
    3. Correlation insights
    4. Predictive indicators
    
    Logs:
    {logs}
    """
}

def get_prompt_template(template_name: str) -> str:
    """Get a prompt engineering template."""
    return PROMPT_TEMPLATES.get(template_name, PROMPT_TEMPLATES['error_analysis'])

# Global LLM manager instance
llm_manager = LLMManager()