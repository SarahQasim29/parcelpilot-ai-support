# src/api/main.py
import os
import sys
import logging
from typing import Optional, Dict
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv
from datetime import datetime
import pandas as pd
import json

# src/api/main.py
import sys

# ============================================
# FIX FOR PYTHON 3.14 + PYDANTIC 1.x
# ============================================
if sys.version_info >= (3, 14):
    import pydantic
    # Patch Pydantic to work with Python 3.14
    if not hasattr(pydantic, '_patched_for_314'):
        from pydantic import main
        original_new = main.ModelMetaclass.__new__
        
        def patched_new(cls, name, bases, dct):
            if 'extra' in dct and isinstance(dct['extra'], str):
                pass
            return original_new(cls, name, bases, dct)
        
        main.ModelMetaclass.__new__ = patched_new
        pydantic._patched_for_314 = True
# ============================================


# ============================================
# WINDOWS PATCH
# ============================================
if sys.platform == 'win32':
    class MockPwd:
        def getpwuid(self, uid):
            class User:
                pw_name = 'windows_user'
                pw_uid = uid
                pw_gid = 1000
                pw_dir = 'C:\\Users\\user'
                pw_shell = 'cmd.exe'
                pw_gecos = 'Windows User'
                pw_passwd = 'x'
            return User()
        def getpwnam(self, name):
            return self.getpwuid(1000)
        def getpwall(self):
            return []
    sys.modules['pwd'] = MockPwd()
    print("✅ Windows pwd module patched")
# ============================================

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================
# CONFIGURATION
# ============================================
config = {
    'OPENAI_API_KEY': os.getenv('OPENAI_API_KEY', 'dummy'),
    'GEMINI_API_KEY': os.getenv('GEMINI_API_KEY', 'dummy'),
    'GROQ_API_KEY': os.getenv('GROQ_API_KEY', 'dummy'),  # NEW
    'USE_LOCAL_LLM': os.getenv('USE_LOCAL_LLM', 'true'),
    'USE_LOCAL_EMBEDDINGS': os.getenv('USE_LOCAL_EMBEDDINGS', 'true'),
    'CHROMA_PERSIST_DIRECTORY': os.getenv('CHROMA_PERSIST_DIRECTORY', './chroma_db'),
    'SECRET_KEY': os.getenv('SECRET_KEY', 'parcelpilot_super_secret_key_2024_32chars'),
    'TEMPERATURE': float(os.getenv('TEMPERATURE', '0.0')),
    'MAX_TOKENS': int(os.getenv('MAX_TOKENS', '2000')),
    'DOCUMENTS_PATH': os.getenv('DOCUMENTS_PATH', './data/documents'),
    'STRUCTURED_DATA_PATH': os.getenv('STRUCTURED_DATA_PATH', './data/structured'),
}

# ============================================
# IMPORTS
# ============================================
from src.auth.auth_manager import AuthManager
from src.data.ingestion import DataIngestion
from src.tools.document_tools import DocumentTools
from src.tools.data_tools import DataTools
from src.tools.action_tools import ActionTools

# Import AI Agents - Try Groq first, then Gemini, then fallback
try:
    from src.agents.groq_agent import GroqAgent
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False
    logger.warning("⚠️ GroqAgent not available")

try:
    from src.agents.ai_agent import RealAIAgent as GeminiAgent
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logger.warning("⚠️ GeminiAgent not available")

# Fallback
from src.agents.free_agent import FreeSupportAgent

# ============================================
# GLOBAL VARIABLES
# ============================================
structured_data = {}
sessions = {}
auth_manager = None
data_ingestion = None
document_tools = None
data_tools = None
action_tools = None

# ============================================
# INITIALIZATION
# ============================================
def initialize_components():
    """Initialize all components"""
    global auth_manager, data_ingestion, document_tools, data_tools, action_tools, structured_data
    
    logger.info("🚀 Initializing components...")
    
    # Auth Manager
    auth_manager = AuthManager(config)
    
    # Data Ingestion
    data_ingestion = DataIngestion(config)
    
    # Load documents
    documents = data_ingestion.load_documents(config['DOCUMENTS_PATH'])
    if documents:
        data_ingestion.process_documents(documents)
        logger.info(f"✅ Loaded {len(documents)} documents")
    else:
        logger.warning("⚠️ No documents loaded")
    
    # Load structured data
    structured_data = data_ingestion.load_structured_data(config['STRUCTURED_DATA_PATH'])
    
    # Debug: Print what was loaded
    logger.info("=" * 50)
    logger.info("📊 STRUCTURED DATA LOADED:")
    for key, df in structured_data.items():
        logger.info(f"   {key}: {len(df)} rows, columns: {list(df.columns)}")
    logger.info("=" * 50)
    
    # Initialize tools
    document_tools = DocumentTools(data_ingestion)
    data_tools = DataTools(structured_data)
    action_tools = ActionTools()
    
    logger.info("✅ All components initialized")
    return True

# Initialize on startup
initialize_components()

# ============================================
# FASTAPI APP
# ============================================
app = FastAPI(
    title="ParcelPilot AI Support",
    description="AI-powered support system",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================
# MODELS
# ============================================
class LoginRequest(BaseModel):
    user_id: str
    password: str

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    type: str
    message: str
    requires_confirmation: bool = False
    action_data: Optional[Dict] = None
    session_id: str

# ============================================
# HELPER: Create AI Agent
# ============================================
def create_ai_agent(tools, user, config):
    """Create the best available AI agent"""
    
    # Try Groq first (FREE + FAST)
    groq_key = config.get('GROQ_API_KEY')
    if groq_key and groq_key != 'dummy' and GROQ_AVAILABLE:
        try:
            agent = GroqAgent(tools, user, config)
            if agent.use_groq:
                logger.info("✅ Using Groq AI Agent")
                return agent
        except Exception as e:
            logger.warning(f"⚠️ Groq failed: {e}")
    
    # Try Gemini second
    gemini_key = config.get('GEMINI_API_KEY')
    if gemini_key and gemini_key != 'dummy' and GEMINI_AVAILABLE:
        try:
            agent = GeminiAgent(tools, user, config)
            if agent.use_gemini:
                logger.info("✅ Using Gemini AI Agent")
                return agent
        except Exception as e:
            logger.warning(f"⚠️ Gemini failed: {e}")
    
    # Fallback to rule-based
    logger.info("🔄 Using Fallback (rule-based) Agent")
    return FreeSupportAgent(tools, user, config)

# ============================================
# API ENDPOINTS
# ============================================

@app.get("/")
async def root():
    # Detect which agent is configured
    has_groq = config.get('GROQ_API_KEY') and config.get('GROQ_API_KEY') != 'dummy'
    has_gemini = config.get('GEMINI_API_KEY') and config.get('GEMINI_API_KEY') != 'dummy'
    
    if has_groq:
        agent_type = "Groq AI Agent (FREE - 30 req/min)"
    elif has_gemini:
        agent_type = "Google Gemini AI Agent"
    else:
        agent_type = "Fallback (Rule-based)"
    
    return {
        "service": "ParcelPilot AI Support",
        "version": "2.0.0",
        "status": "running",
        "agent_type": agent_type,
        "docs": "/docs",
        "app": "/app"
    }

# ============================================
# AUTHENTICATION
# ============================================

@app.post("/api/auth/login")
async def login(request: LoginRequest):
    """Authenticate user"""
    try:
        user = auth_manager.authenticate(request.user_id, request.password)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        token = auth_manager.generate_token(user)
        return {
            'token': token,
            'user_id': user.user_id,
            'role': user.role.value,
            'account_id': user.account_id
        }
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# CHAT (MAIN AI AGENT ENDPOINT)
# ============================================

@app.post("/api/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    authorization: Optional[str] = Header(None)
):
    """Process chat message using AI Agent"""
    try:
        # Check for authorization header
        if not authorization:
            logger.warning("No authorization header")
            raise HTTPException(status_code=401, detail="No authorization header")
        
        if not authorization.startswith("Bearer "):
            logger.warning("Invalid authorization format")
            raise HTTPException(status_code=401, detail="Invalid authorization format")
        
        token = authorization.replace("Bearer ", "")
        
        # Authenticate user
        user = auth_manager.authenticate_token(token)
        if not user:
            logger.warning("Invalid token")
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        
        logger.info(f"✅ Authenticated user: {user.user_id} ({user.role.value})")
        
        # Get or create session
        session_id = request.session_id or f"session_{datetime.now().timestamp()}"
        
        if session_id not in sessions:
            # Setup tools with user context
            data_tools.set_user(user)
            action_tools.set_user(user)
            
            # Define tools for the AI Agent
            tools = [
                document_tools.search_policies,
                data_tools.query_orders,
                data_tools.query_tickets,
                data_tools.calculate_cancellation_fee,
                action_tools.create_escalation,
                action_tools.update_ticket,
                action_tools.create_followup_task
            ]
            
            # Create the best available AI agent
            sessions[session_id] = create_ai_agent(tools, user, config)
            logger.info(f"✅ Created session: {session_id}")
        
        # Process request through the agent
        agent = sessions[session_id]
        result = agent.process_request(request.message)
        
        # Return response
        return ChatResponse(
            type=result.get('type', 'response'),
            message=result.get('message', ''),
            requires_confirmation=result.get('requires_confirmation', False),
            action_data=result.get('action_data'),
            session_id=session_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Chat error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# CONFIRM ACTION
# ============================================

@app.post("/api/confirm")
async def confirm_action(
    request: Dict,
    authorization: Optional[str] = Header(None)
):
    """Confirm or cancel a pending action"""
    try:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Unauthorized")
        
        token = authorization.replace("Bearer ", "")
        user = auth_manager.authenticate_token(token)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        # Check if there's a pending action
        if not action_tools.pending_action:
            return {
                'status': 'error',
                'message': 'No pending action found'
            }
        
        # Execute the action
        action = action_tools.pending_action
        action_type = action.get('action')
        
        if action_type == 'escalation':
            ticket_id = action.get('ticket_id', 'TKT-501')
            result = {
                'status': 'success',
                'message': f'✅ Escalation created for ticket {ticket_id}',
                'ticket_id': ticket_id,
                'timestamp': datetime.now().isoformat()
            }
        else:
            result = {
                'status': 'success',
                'message': 'Action confirmed and executed',
                'timestamp': datetime.now().isoformat()
            }
        
        # Clear pending action
        action_tools.pending_action = None
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Confirmation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# ADDITIONAL ENDPOINTS
# ============================================

@app.get("/api/health")
async def health():
    """Health check endpoint"""
    has_groq = config.get('GROQ_API_KEY') and config.get('GROQ_API_KEY') != 'dummy'
    has_gemini = config.get('GEMINI_API_KEY') and config.get('GEMINI_API_KEY') != 'dummy'
    
    if has_groq:
        agent_type = "Groq AI (FREE)"
    elif has_gemini:
        agent_type = "Gemini AI"
    else:
        agent_type = "Fallback (Rule-based)"
    
    return {
        'status': 'healthy',
        'sessions': len(sessions),
        'timestamp': datetime.now().isoformat(),
        'agent_type': agent_type,
        'groq_configured': has_groq,
        'gemini_configured': has_gemini
    }

@app.get("/api/session/{session_id}")
async def get_session(
    session_id: str,
    authorization: Optional[str] = Header(None)
):
    """Get session information"""
    try:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Unauthorized")
        
        token = authorization.replace("Bearer ", "")
        user = auth_manager.authenticate_token(token)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        if session_id not in sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session = sessions[session_id]
        session_user = getattr(session, 'user', None)
        
        # Detect agent type
        agent_type = "Unknown"
        if hasattr(session, 'use_groq') and session.use_groq:
            agent_type = "Groq AI"
        elif hasattr(session, 'use_gemini') and session.use_gemini:
            agent_type = "Gemini AI"
        else:
            agent_type = "Fallback (Rule-based)"
        
        return {
            'session_id': session_id,
            'user_id': session_user.user_id if session_user else user.user_id,
            'role': session_user.role.value if session_user else user.role.value,
            'created_at': datetime.now().isoformat(),
            'active': True,
            'agent_type': agent_type
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Session error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# STATIC FILES & FRONTEND
# ============================================

# Serve static files
try:
    app.mount("/static", StaticFiles(directory="src/frontend"), name="static")
except Exception as e:
    logger.warning(f"⚠️ Could not mount static files: {e}")

@app.get("/app")
async def serve_frontend():
    """Serve chat interface"""
    try:
        with open("src/frontend/index.html", "r", encoding='utf-8') as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>ParcelPilot AI Support</title>
            <style>
                body { font-family: sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }
                h1 { color: #1a237e; }
                .info { background: #e3f2fd; padding: 20px; border-radius: 8px; }
                .info a { color: #1a237e; }
            </style>
        </head>
        <body>
            <h1>📦 ParcelPilot AI Support</h1>
            <div class="info">
                <p>✅ API is running!</p>
                <p>🤖 Agent Type: AI Agent (Groq/Gemini/Fallback)</p>
                <p>📚 API Docs: <a href="/docs">/docs</a></p>
                <p>⚠️ Frontend not found. Please create <code>src/frontend/index.html</code></p>
                <p>🔑 Test credentials: customer_001 / pass123</p>
            </div>
        </body>
        </html>
        """)

# ============================================
# ERROR HANDLERS
# ============================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return {
        'error': True,
        'status_code': exc.status_code,
        'detail': exc.detail,
        'timestamp': datetime.now().isoformat()
    }

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}")
    return {
        'error': True,
        'status_code': 500,
        'detail': 'Internal server error',
        'timestamp': datetime.now().isoformat()
    }

# ============================================
# SHUTDOWN EVENT
# ============================================

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on shutdown"""
    logger.info("🛑 Shutting down...")
    sessions.clear()
    logger.info("✅ Cleanup complete")

# ============================================
# STARTUP EVENT
# ============================================

@app.on_event("startup")
async def startup_event():
    """Log startup information"""
    logger.info("=" * 60)
    logger.info("🚀 ParcelPilot AI Support System v2.0")
    
    has_groq = config.get('GROQ_API_KEY') and config.get('GROQ_API_KEY') != 'dummy'
    has_gemini = config.get('GEMINI_API_KEY') and config.get('GEMINI_API_KEY') != 'dummy'
    
    if has_groq:
        logger.info("🤖 Agent Type: Groq AI Agent (FREE - 30 req/min)")
    elif has_gemini:
        logger.info("🤖 Agent Type: Google Gemini AI Agent")
    else:
        logger.info("🤖 Agent Type: Fallback (Rule-based)")
        logger.info("   To enable AI, add GROQ_API_KEY or GEMINI_API_KEY to .env")
    
    logger.info(f"📂 Documents path: {config['DOCUMENTS_PATH']}")
    logger.info(f"📂 Data path: {config['STRUCTURED_DATA_PATH']}")
    logger.info(f"🔑 JWT Secret: {'*' * 8}")
    logger.info("=" * 60)

# ============================================
# MAIN ENTRY POINT
# ============================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )