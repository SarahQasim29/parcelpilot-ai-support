# 📦 ParcelPilot AI Support System

**An AI-powered customer support system for a B2B logistics platform**

> Built for the **CalQuity AI Engineer Assessment** - A real AI agent with natural language understanding, tool-calling, multi-step reasoning, and trust-aware responses.

---

## 🎯 Overview

ParcelPilot is a B2B logistics platform where customers book and manage shipments across multiple carriers. This system provides an **AI-powered support agent** that handles customer inquiries about orders, tickets, policies, cancellations, service credits, and SLAs.

The system uses a **real AI agent** (powered by Groq) with:
- Natural language understanding
- Tool-calling capabilities
- Step-by-step reasoning
- Access control and data privacy
- Source reliability scoring
- Confirmation workflow for actions

---

## ✨ Features

### 1. 🤖 Real AI Agent
- Powered by **Groq** (openai/gpt-oss-120b) - FREE and FAST (30 requests/min)
- Natural language understanding (not just pattern matching)
- Step-by-step reasoning
- Tool-calling capabilities

### 2. 🔍 Intelligent Tools
| Tool | Purpose |
|------|---------|
| **Document Search** | Search policies, agreements, SOPs with reliability scoring |
| **Data Query** | Query orders, tickets, accounts with access control |
| **State-Changing Actions** | Escalations, ticket updates, follow-up tasks with confirmation |

### 3. 🔐 Access Control
- Customers see ONLY their own data
- Support agents see all accounts
- Ops managers see all + monitoring
- Access enforced at data/tool layer (not just UI)

### 4. 🧠 Multi-Step Reasoning
The AI thinks step by step:
1. Understands the question
2. Identifies needed information
3. Calls appropriate tools
4. Reasons about the results
5. Provides clear, helpful answers

### 5. ✅ Trust & Reliability
- Documents have reliability scores (0.3 - 1.0)
- Customer agreements override general policies
- Historical tickets flagged as "may be incorrect"
- Source conflicts handled deliberately

### 6. 📊 Proactive Monitoring
- Detects complaint surges
- Identifies SLA violations
- Finds recurring issues
- Alerts ops team automatically


---

## 🛠️ Tech Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **AI Model** | Groq (openai/gpt-oss-120b) | Natural language understanding |
| **Backend** | FastAPI | API server |
| **Frontend** | HTML/CSS/JavaScript | Chat interface |
| **Vector DB** | ChromaDB | Document storage and retrieval |
| **Embeddings** | Sentence Transformers | Document vectorization |
| **Data** | Pandas, OpenPyXL | Excel data processing |
| **Auth** | JWT | Authentication |
| **Deployment** | Render | Hosting |

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Groq API key ([Get it free](https://console.groq.com))
- Git

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/SarahQasim29/parcelpilot-ai-support.git
cd parcelpilot-ai-support

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create .env file
cp .env.example .env
# Edit .env and add your GROQ_API_KEY

# 5. Run the application
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000


# Required
GROQ_API_KEY=your_groq_api_key_here

# Optional (fallback)
GEMINI_API_KEY=your_gemini_api_key_here
OPENAI_API_KEY=your_openai_api_key_here

# Security
SECRET_KEY=your_super_secret_key_here

# Settings
DEBUG=True
LOG_LEVEL=INFO

Test Credentials
Role	User ID	Password
Customer	customer_001	pass123
Support	support_001	support123
Ops	ops_001	ops123
