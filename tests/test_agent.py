# tests/test_agent.py
import pytest
import asyncio
from src.agents.support_agent import SupportAgent
from src.auth.auth_manager import AuthManager, UserRole

@pytest.fixture
def auth_manager():
    return AuthManager({})

@pytest.fixture
def user(auth_manager):
    return auth_manager.authenticate('customer_001', 'pass123')

@pytest.fixture
def agent(user):
    # Mock tools and config
    tools = []
    config = {
        'OPENAI_API_KEY': 'test_key',
        'LLM_MODEL': 'gpt-3.5-turbo',
        'TEMPERATURE': 0.0,
        'MAX_TOKENS': 1000
    }
    return SupportAgent(tools, user, config)

def test_agent_initialization(agent):
    assert agent is not None
    assert agent.user is not None
    assert agent.user.role == UserRole.CUSTOMER

@pytest.mark.asyncio
async def test_process_request(agent):
    result = agent.process_request("Hello")
    assert result['type'] == 'response'
    assert 'message' in result