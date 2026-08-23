# test_ai_agent.py
"""
Test the Real AI Agent with various questions
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_agent():
    # Login
    print("🔐 Logging in...")
    login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
        "user_id": "customer_001",
        "password": "pass123"
    })
    token = login_resp.json().get('token')
    print(f"✅ Logged in. Token: {token[:20]}...")
    
    # Test questions
    questions = [
        "Can Northstar cancel ORD-1001 without a cancellation fee? Explain why.",
        "A pickup is three hours late because of carrier fault. Should I get a service credit?",
        "Show me my orders",
        "What's the status of ORD-1001?",
        "Is TKT-501 resolved?",
        "What's the refund policy for shipments over 50kg?",
        "What are Northstar's special terms?",
        "Escalate TKT-501"
    ]
    
    print("\n🧠 Testing Real AI Agent...")
    print("=" * 60)
    
    for question in questions:
        print(f"\n👤 You: {question}")
        
        response = requests.post(f"{BASE_URL}/api/chat", 
            headers={"Authorization": f"Bearer {token}"},
            json={"message": question}
        )
        
        data = response.json()
        print(f"🤖 AI: {data.get('message', 'No response')}")
        print("-" * 60)

if __name__ == "__main__":
    test_agent()