# src/agents/support_agent.py
from typing import List, Dict, Any, Optional
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain.schema import SystemMessage, HumanMessage, AIMessage
import logging
import json
from datetime import datetime

logger = logging.getLogger(__name__)

class SupportAgent:
    def __init__(self, tools: List, user, config: Dict):
        self.tools = tools
        self.user = user
        self.config = config
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True,
            output_key="output"
        )
        
        # Initialize LLM
        self.llm = ChatOpenAI(
            model=config.get('LLM_MODEL', 'gpt-4'),
            temperature=config.get('TEMPERATURE', 0.0),
            openai_api_key=config.get('OPENAI_API_KEY'),
            max_tokens=config.get('MAX_TOKENS', 2000)
        )
        
        # Create agent prompt
        self.prompt = self._create_prompt()
        
        # Create agent
        self.agent = create_openai_tools_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=self.prompt
        )
        
        self.agent_executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            memory=self.memory,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=5,
            early_stopping_method="generate"
        )
        
        # Track conversation
        self.conversation_id = None
        self.start_time = datetime.now()
    
    def _create_prompt(self):
        """Create the agent prompt template"""
        return ChatPromptTemplate.from_messages([
            SystemMessage(content=f"""You are an AI support assistant for ParcelPilot, a B2B logistics platform.

Your role is to help {self.user.role.value}s with their support needs.

IMPORTANT GUIDELINES:

1. **Source Reliability**: 
   - Current policies (v3) have high reliability (1.0)
   - Customer agreements override general policies
   - Deprecated policies (v2) have low reliability (0.3)
   - Historical tickets may contain incorrect information

2. **Access Control**:
   - You can access data based on user permissions
   - Customers can only see their own data
   - Support agents can see all data for support purposes
   - Ops managers have access to monitoring and analytics

3. **Actions**:
   - Any state-changing action requires explicit user confirmation
   - Always ask for confirmation before performing actions
   - If unsure, escalate to human support

4. **Response Quality**:
   - Be clear and concise
   - Cite sources when providing information
   - If information conflicts, explain the conflict and recommend escalation
   - If you don't know something, say so and offer to escalate

5. **Current User Context**:
   - User ID: {self.user.user_id}
   - Role: {self.user.role.value}
   - Account ID: {self.user.account_id or 'None (support user)'}
   - Permissions: {', '.join(self.user.permissions)}

Always maintain a professional, helpful tone. If you need to escalate to a human support agent, clearly explain why.
"""),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad")
        ])
    
    def process_request(self, user_input: str) -> Dict[str, Any]:
        """Process a user request through the agent"""
        try:
            # Log the request
            logger.info(f"Processing request from {self.user.user_id}: {user_input[:100]}...")
            
            # Check for confirmation responses
            if self._is_confirmation_response(user_input):
                return self._handle_confirmation(user_input)
            
            # Process through agent
            response = self.agent_executor.invoke({
                "input": user_input,
                "user_context": self.user
            })
            
            output = response.get('output', '')
            
            # Check if response contains an action that needs confirmation
            if 'pending_confirmation' in output.lower():
                return {
                    'type': 'action_required',
                    'message': output,
                    'requires_confirmation': True,
                    'action_data': self._extract_action_data(output)
                }
            
            return {
                'type': 'response',
                'message': output,
                'requires_confirmation': False
            }
            
        except Exception as e:
            logger.error(f"Error processing request: {str(e)}")
            return {
                'type': 'error',
                'message': f"An error occurred: {str(e)}",
                'requires_confirmation': False
            }
    
    def _is_confirmation_response(self, user_input: str) -> bool:
        """Check if user input is a confirmation response"""
        confirmation_phrases = ['yes', 'confirm', 'proceed', 'ok', 'okay', 
                               'sure', 'go ahead', 'do it', 'approve']
        return any(phrase in user_input.lower() for phrase in confirmation_phrases)
    
    def _handle_confirmation(self, user_input: str) -> Dict:
        """Handle user confirmation of an action"""
        # In production, this would get the pending action from the session
        return {
            'type': 'confirmation',
            'message': 'Action confirmed and executed.',
            'requires_confirmation': False
        }
    
    def _extract_action_data(self, output: str) -> Dict:
        """Extract action data from agent output"""
        try:
            # Try to parse JSON from output
            import re
            json_match = re.search(r'\{.*\}', output, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass
        
        return {'action': 'unknown', 'data': {}}
    
    def get_conversation_summary(self) -> Dict:
        """Get summary of the conversation"""
        return {
            'user_id': self.user.user_id,
            'role': self.user.role.value,
            'start_time': self.start_time.isoformat(),
            'duration': str(datetime.now() - self.start_time),
            'message_count': len(self.memory.chat_memory.messages) // 2
        }