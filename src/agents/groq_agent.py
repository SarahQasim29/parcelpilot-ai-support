# src/agents/groq_agent.py
"""
AI Agent powered by Groq - Using working models!
"""

import logging
import json
import re
from typing import List, Dict, Any
from groq import Groq

logger = logging.getLogger(__name__)


class GroqAgent:
    """
    Real AI Agent powered by Groq API
    Uses working models from the API
    """
    
    def __init__(self, tools: List, user, config: Dict):
        self.tools = tools
        self.user = user
        self.config = config
        self.client = None
        self.use_groq = False
        
        # Confirmed working models
        self.models = [
            "openai/gpt-oss-120b",
            "openai/gpt-oss-20b",
            "qwen/qwen3.6-27b",
            "groq/compound",
        ]
        
        self._init_groq()
        
        if self.use_groq:
            logger.info(f"✅ REAL AI AGENT with Groq for {user.user_id}")
        else:
            logger.warning(f"⚠️ AI Agent failed, using fallback")
    
    def _init_groq(self):
        """Initialize Groq with automatic model selection"""
        api_key = self.config.get('GROQ_API_KEY')
        
        if not api_key or api_key == 'dummy':
            logger.error("❌ No Groq API key found!")
            return
        
        try:
            self.client = Groq(api_key=api_key)
            
            for model in self.models:
                try:
                    response = self.client.chat.completions.create(
                        model=model,
                        messages=[{"role": "user", "content": "Say OK"}],
                        temperature=0.1,
                        max_tokens=5
                    )
                    if response and response.choices:
                        self.model = model
                        self.use_groq = True
                        logger.info(f"✅ Groq initialized with: {model}")
                        return
                except Exception as e:
                    logger.warning(f"Model {model} failed: {e}")
                    continue
            
            logger.error("❌ No Groq model worked!")
            
        except Exception as e:
            logger.error(f"❌ Groq init error: {e}")
    
    def _get_messages(self, user_input: str, tool_result: str = None) -> List:
        """Build messages for Groq - NO TOOL CALLING, just instructions"""
        
        system_prompt = f"""You are an AI support agent for ParcelPilot. You have REAL reasoning capabilities.

## USER CONTEXT:
- User ID: {self.user.user_id}
- Role: {self.user.role.value}
- Account ID: {self.user.account_id or 'None'}
- Account Name: Northstar Logistics (ACCT-001)

## IMPORTANT RULES:
1. You are an AI AGENT with reasoning - THINK step by step
2. ONLY access data for ACCT-001 (Northstar Logistics)
3. For actions (escalation), ASK FOR CONFIRMATION first
4. Historical tickets may have incorrect info - WARN about this

## DATA AVAILABLE:
You have access to these functions. When you need data, respond with:
FUNCTION: function_name(param1="value1", param2="value2")

Available functions:
- query_orders(order_id="ORD-1001") - Get order details
- query_tickets(ticket_id="TKT-501") - Get ticket details  
- search_policies(query="cancellation policy") - Search documents
- calculate_cancellation_fee(order_id="ORD-1001") - Check cancellation fee

## ACCOUNT MAPPING:
- ACCT-001 = Northstar Logistics (Enterprise, Priya Mehta)
- ACCT-002 = LumenWorks (Growth, Arjun Rao)
- ACCT-003 = Beacon Retail (Standard, Neha Kapoor)
- ACCT-004 = Axis Labs (Enterprise, Priya Mehta)

## INSTRUCTIONS:
1. THINK step by step
2. Use FUNCTIONS when you need information
3. Reason about the data you receive
4. Provide clear, helpful answers
5. For escalations, say: "Please confirm if you want to escalate"

## USER QUESTION:
{user_input}

Now think step by step and respond:"""
        
        messages = [{"role": "system", "content": system_prompt}]
        messages.append({"role": "user", "content": user_input})
        
        if tool_result:
            messages.append({"role": "assistant", "content": f"Function result: {tool_result}"})
            messages.append({"role": "user", "content": "Now provide your final answer based on this data."})
        
        return messages
    
    def _call_function(self, function_name: str, args: Dict) -> str:
        """Execute a function and return the result"""
        for tool in self.tools:
            if hasattr(tool, '__name__') and tool.__name__ == function_name:
                try:
                    result = tool(**args)
                    return str(result)
                except Exception as e:
                    return f"Function error: {str(e)}"
            if hasattr(tool, 'name') and tool.name == function_name:
                try:
                    result = tool(**args)
                    return str(result)
                except Exception as e:
                    return f"Function error: {str(e)}"
        return f"Function '{function_name}' not found"
    
    def _extract_function_call(self, text: str) -> Dict:
        """Extract function call from AI response"""
        patterns = [
            r'FUNCTION:\s*(\w+)\((.*?)\)',
            r'\[FUNCTION\]\s*(\w+)\((.*?)\)',
            r'use\s+(\w+)\((.*?)\)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                function_name = match.group(1).strip()
                args_str = match.group(2).strip()
                
                args = {}
                if args_str:
                    for pair in args_str.split(','):
                        pair = pair.strip()
                        if '=' in pair:
                            key, value = pair.split('=', 1)
                            args[key.strip()] = value.strip().strip('"\'')
                        else:
                            args['query'] = pair.strip('"\'')
                
                return {'found': True, 'function_name': function_name, 'args': args}
        
        return {'found': False}
    
    def process_request(self, user_input: str) -> Dict:
        """Process user request with REAL AI reasoning"""
        try:
            if not self.use_groq:
                return self._fallback(user_input)
            
            logger.info(f"🧠 AI: {user_input[:50]}...")
            
            # First pass - AI thinks and decides
            messages = self._get_messages(user_input)
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.1,
                max_tokens=1500
            )
            text = response.choices[0].message.content
            
            # Check if AI wants to use a function
            function_call = self._extract_function_call(text)
            
            if function_call['found']:
                # Execute the function
                result = self._call_function(function_call['function_name'], function_call['args'])
                
                # AI reasons about the function result
                final_messages = self._get_messages(user_input, result)
                final_response = self.client.chat.completions.create(
                    model=self.model,
                    messages=final_messages,
                    temperature=0.1,
                    max_tokens=1500
                )
                final_text = final_response.choices[0].message.content
                
                if 'confirm' in final_text.lower():
                    return {
                        'type': 'action_required',
                        'message': final_text,
                        'requires_confirmation': True,
                        'action_data': {'action': 'escalation'}
                    }
                
                return {
                    'type': 'response',
                    'message': final_text,
                    'requires_confirmation': False,
                    'action_data': None
                }
            
            # No function needed
            if 'confirm' in text.lower():
                return {
                    'type': 'action_required',
                    'message': text,
                    'requires_confirmation': True,
                    'action_data': {'action': 'escalation'}
                }
            
            return {
                'type': 'response',
                'message': text,
                'requires_confirmation': False,
                'action_data': None
            }
            
        except Exception as e:
            logger.error(f"❌ AI error: {e}")
            return self._fallback(user_input)
    
    def _fallback(self, user_input: str) -> Dict:
        """Fallback when AI fails"""
        try:
            from src.agents.free_agent import FreeSupportAgent
            fallback = FreeSupportAgent(self.tools, self.user, self.config)
            return fallback.process_request(user_input)
        except:
            return {
                'type': 'response',
                'message': "AI unavailable. Try: Show me my orders | What's the status of ORD-1001? | Show me my tickets",
                'requires_confirmation': False,
                'action_data': None
            }