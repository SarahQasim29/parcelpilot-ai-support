# src/agents/ai_agent.py
"""
Real AI Agent with Google Gemini (using latest models)
"""

import logging
import json
import re
from typing import List, Dict, Any, Optional
import google.generativeai as genai

logger = logging.getLogger(__name__)


class RealAIAgent:
    """
    Real AI Agent powered by Google Gemini
    """
    
    def __init__(self, tools: List, user, config: Dict):
        self.tools = tools
        self.user = user
        self.config = config
        self.model = None
        self.use_gemini = False
        
        # Try to initialize Gemini
        self._init_gemini()
        
        if self.use_gemini:
            logger.info(f"✅ Real AI Agent with Gemini for {user.user_id}")
        else:
            logger.warning(f"⚠️ Using fallback for {user.user_id}")
    
    def _init_gemini(self):
        """Initialize Gemini with automatic model detection"""
        api_key = self.config.get('GEMINI_API_KEY')
        
        if not api_key or api_key == 'dummy':
            logger.warning("⚠️ No Gemini API key found. Add GEMINI_API_KEY to .env")
            self.use_gemini = False
            return
        
        try:
            # Configure Gemini
            genai.configure(api_key=api_key)
            
            # Get available models
            try:
                models = genai.list_models()
                available_models = [m.name for m in models if 'generateContent' in m.supported_generation_methods]
                logger.info(f"📋 Available models: {available_models}")
            except Exception as e:
                logger.warning(f"Could not list models: {e}")
                available_models = []
            
            # Try models in order - UPDATED with new model names!
            model_names = [
                "models/gemini-2.5-flash",      # Fast, good quality
                "models/gemini-flash-latest",    # Fastest
                "models/gemini-2.5-pro",         # Best quality
                "models/gemini-pro-latest",      # Good quality
                "models/gemini-3.5-flash",       # Newer
                "models/gemini-flash-lite-latest",
            ]
            
            selected_model = None
            for name in model_names:
                if name in available_models:
                    try:
                        self.model = genai.GenerativeModel(
                            model_name=name,
                            generation_config={
                                "temperature": 0.1,
                                "max_output_tokens": 2000,
                                "top_p": 0.95,
                            }
                        )
                        # Test it
                        test = self.model.generate_content("Say OK")
                        if test and test.text:
                            selected_model = name
                            self.use_gemini = True
                            logger.info(f"✅ Gemini initialized with: {name}")
                            break
                    except Exception as e:
                        logger.warning(f"Failed with {name}: {e}")
            
            if not self.use_gemini:
                logger.error("❌ No Gemini model worked. Check your API key.")
                self.use_gemini = False
                
        except Exception as e:
            logger.error(f"❌ Gemini init error: {e}")
            self.use_gemini = False
    
    def _get_prompt(self, user_input: str, tool_result: str = None) -> str:
        """Build prompt for Gemini"""
        
        system_prompt = f"""You are an AI support agent for ParcelPilot, a logistics platform.

## USER CONTEXT:
- User ID: {self.user.user_id}
- Role: {self.user.role.value}
- Account ID: {self.user.account_id or 'None'}
- Account Name: Northstar Logistics (if ACCT-001)

## IMPORTANT RULES:
1. You can ONLY access data for ACCT-001 (Northstar Logistics)
2. For any action (escalation), ASK FOR CONFIRMATION: "Please confirm if you want to..."
3. Historical tickets may have incorrect information - warn about this
4. If you don't know something, say "I'm not sure" and offer to escalate

## ACCOUNT MAPPING:
- ACCT-001 = Northstar Logistics (Enterprise, Priya Mehta, premium support)
- ACCT-002 = LumenWorks (Growth, Arjun Rao)
- ACCT-003 = Beacon Retail (Standard, Neha Kapoor)
- ACCT-004 = Axis Labs (Enterprise, Priya Mehta)

## TOOLS AVAILABLE:
When you need information, use:
- TOOL: search_policies(query="text") - Search documents
- TOOL: query_orders(order_id="ORD-1001") - Get order details
- TOOL: query_tickets(ticket_id="TKT-501") - Get ticket details
- TOOL: calculate_cancellation_fee(order_id="ORD-1001") - Check cancellation fee

## INSTRUCTIONS:
1. Think step by step
2. Use tools when you need data
3. Provide clear, helpful answers
4. Cite sources when possible
5. For escalations, ask for confirmation first

## USER QUESTION:
{user_input}
"""
        
        if tool_result:
            system_prompt += f"""

## TOOL RESULT:
{tool_result}

Now provide your final answer based on this result."""
        
        return system_prompt
    
    def _call_tool(self, tool_name: str, args: Dict) -> str:
        """Execute a tool and return result"""
        for tool in self.tools:
            # Check by function name
            if hasattr(tool, '__name__') and tool.__name__ == tool_name:
                try:
                    result = tool(**args)
                    return str(result)
                except Exception as e:
                    return f"Tool error: {str(e)}"
            # Check by tool name
            if hasattr(tool, 'name') and tool.name == tool_name:
                try:
                    result = tool.invoke(args)
                    return str(result)
                except Exception as e:
                    return f"Tool error: {str(e)}"
        return f"Tool '{tool_name}' not found. Available: {[t.__name__ if hasattr(t, '__name__') else t.name for t in self.tools]}"
    
    def _extract_tool_call(self, text: str) -> Dict:
        """Extract tool call from response"""
        patterns = [
            r'TOOL:\s*(\w+)\((.*?)\)',
            r'\[TOOL\]\s*(\w+)\((.*?)\)',
            r'use\s+(\w+)\((.*?)\)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                tool_name = match.group(1).strip()
                args_str = match.group(2).strip()
                
                # Parse arguments
                args = {}
                if args_str:
                    # Handle key=value pairs
                    for pair in args_str.split(','):
                        pair = pair.strip()
                        if '=' in pair:
                            key, value = pair.split('=', 1)
                            args[key.strip()] = value.strip().strip('"\'')
                        else:
                            args['query'] = pair.strip('"\'')
                
                return {'found': True, 'tool_name': tool_name, 'args': args}
        
        return {'found': False}
    
    def process_request(self, user_input: str) -> Dict:
        """Process user request with Gemini"""
        try:
            # If Gemini not available, use fallback
            if not self.use_gemini:
                logger.info("🔄 Using fallback (Gemini unavailable)")
                return self._fallback_response(user_input)
            
            logger.info(f"🧠 Gemini: {user_input[:50]}...")
            
            # First pass - get response
            prompt = self._get_prompt(user_input)
            response = self.model.generate_content(prompt)
            text = response.text
            
            # Check if tool is needed
            tool_call = self._extract_tool_call(text)
            
            if tool_call['found']:
                # Execute tool
                result = self._call_tool(tool_call['tool_name'], tool_call['args'])
                
                # Second pass - get final response with tool result
                final_prompt = self._get_prompt(user_input, result)
                final_response = self.model.generate_content(final_prompt)
                final_text = final_response.text
                
                # Check for confirmation
                if 'confirm' in final_text.lower() or 'escalate' in final_text.lower():
                    return {
                        'type': 'action_required',
                        'message': final_text,
                        'requires_confirmation': True,
                        'action_data': {'action': 'escalation', 'ticket_id': 'TKT-501'}
                    }
                
                return {
                    'type': 'response',
                    'message': final_text,
                    'requires_confirmation': False,
                    'action_data': None
                }
            
            # No tool call
            if 'confirm' in text.lower() or 'escalate' in text.lower():
                return {
                    'type': 'action_required',
                    'message': text,
                    'requires_confirmation': True,
                    'action_data': {'action': 'escalation', 'ticket_id': 'TKT-501'}
                }
            
            return {
                'type': 'response',
                'message': text,
                'requires_confirmation': False,
                'action_data': None
            }
            
        except Exception as e:
            logger.error(f"❌ Gemini error: {e}")
            return self._fallback_response(user_input)
    
    def _fallback_response(self, user_input: str) -> Dict:
        """Fallback when Gemini fails"""
        try:
            from src.agents.free_agent import FreeSupportAgent
            fallback = FreeSupportAgent(self.tools, self.user, self.config)
            return fallback.process_request(user_input)
        except Exception as e:
            logger.error(f"❌ Fallback error: {e}")
            return {
                'type': 'response',
                'message': "I'm currently unavailable. Please try:\n• Show me my orders\n• What's the status of ORD-1001?\n• Show me my tickets\n\nOr contact support.",
                'requires_confirmation': False,
                'action_data': None
            }