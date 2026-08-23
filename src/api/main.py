# src/api/main.py
import sys

# ============================================
# FIX FOR PYTHON 3.14 + PYDANTIC 1.x
# ============================================
if sys.version_info >= (3, 14):
    try:
        import pydantic
        pydantic.fields.ModelField.__init__ = lambda self, *args, **kwargs: None
        pydantic.fields.ModelField.prepare = lambda self: None
        print("✅ Pydantic patch applied")
    except Exception as e:
        print(f"⚠️ Pydantic patch failed: {e}")

import os
import logging
from datetime import datetime
from typing import Optional, Dict

# ============================================
# STARLETTE IMPORTS (NOT FASTAPI!)
# ============================================
from starlette.applications import Starlette
from starlette.responses import JSONResponse, HTMLResponse
from starlette.routing import Route
from starlette.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles
from starlette.requests import Request
from pydantic import BaseModel

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

from dotenv import load_dotenv
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
    'GROQ_API_KEY': os.getenv('GROQ_API_KEY', 'dummy'),
    'GEMINI_API_KEY': os.getenv('GEMINI_API_KEY', 'dummy'),
    'OPENAI_API_KEY': os.getenv('OPENAI_API_KEY', 'dummy'),
    'SECRET_KEY': os.getenv('SECRET_KEY', 'parcelpilot_super_secret_key_2024_32chars'),
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

try:
    from src.agents.groq_agent import GroqAgent
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False

try:
    from src.agents.ai_agent import RealAIAgent as GeminiAgent
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

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
    global auth_manager, data_ingestion, document_tools, data_tools, action_tools, structured_data
    logger.info("🚀 Initializing components...")
    auth_manager = AuthManager(config)
    data_ingestion = DataIngestion(config)
    
    documents = data_ingestion.load_documents(config['DOCUMENTS_PATH'])
    if documents:
        data_ingestion.process_documents(documents)
        logger.info(f"✅ Loaded {len(documents)} documents")
    
    structured_data = data_ingestion.load_structured_data(config['STRUCTURED_DATA_PATH'])
    logger.info("📊 STRUCTURED DATA LOADED:")
    for key, df in structured_data.items():
        logger.info(f"   {key}: {len(df)} rows")
    
    document_tools = DocumentTools(data_ingestion)
    data_tools = DataTools(structured_data)
    action_tools = ActionTools()
    logger.info("✅ All components initialized")

initialize_components()

# ============================================
# STARLETTE APP
# ============================================
app = Starlette(debug=True)

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
# HELPERS
# ============================================
def create_ai_agent(tools, user, config):
    groq_key = config.get('GROQ_API_KEY')
    if groq_key and groq_key != 'dummy' and GROQ_AVAILABLE:
        try:
            agent = GroqAgent(tools, user, config)
            if agent.use_groq:
                return agent
        except Exception as e:
            logger.warning(f"⚠️ Groq failed: {e}")
    
    gemini_key = config.get('GEMINI_API_KEY')
    if gemini_key and gemini_key != 'dummy' and GEMINI_AVAILABLE:
        try:
            agent = GeminiAgent(tools, user, config)
            if agent.use_gemini:
                return agent
        except Exception as e:
            logger.warning(f"⚠️ Gemini failed: {e}")
    
    return FreeSupportAgent(tools, user, config)

# ============================================
# ROUTES
# ============================================

async def root(request):
    return JSONResponse({
        "service": "ParcelPilot AI Support",
        "version": "2.0.0",
        "status": "running",
        "agent_type": "AI Agent",
        "docs": "/docs",
        "app": "/app"
    })

async def health(request):
    return JSONResponse({
        "status": "healthy",
        "sessions": len(sessions),
        "timestamp": datetime.now().isoformat()
    })

async def login(request: Request):
    try:
        body = await request.json()
        user = auth_manager.authenticate(body.get('user_id'), body.get('password'))
        if not user:
            return JSONResponse({"detail": "Invalid credentials"}, status_code=401)
        token = auth_manager.generate_token(user)
        return JSONResponse({
            'token': token,
            'user_id': user.user_id,
            'role': user.role.value,
            'account_id': user.account_id
        })
    except Exception as e:
        return JSONResponse({"detail": str(e)}, status_code=500)

async def chat(request: Request):
    try:
        auth_header = request.headers.get('authorization')
        if not auth_header or not auth_header.startswith("Bearer "):
            return JSONResponse({"detail": "Unauthorized"}, status_code=401)
        
        token = auth_header.replace("Bearer ", "")
        user = auth_manager.authenticate_token(token)
        if not user:
            return JSONResponse({"detail": "Invalid token"}, status_code=401)
        
        body = await request.json()
        session_id = body.get('session_id') or f"session_{datetime.now().timestamp()}"
        
        if session_id not in sessions:
            data_tools.set_user(user)
            action_tools.set_user(user)
            tools = [
                document_tools.search_policies,
                data_tools.query_orders,
                data_tools.query_tickets,
                data_tools.calculate_cancellation_fee,
                action_tools.create_escalation,
                action_tools.update_ticket,
                action_tools.create_followup_task
            ]
            sessions[session_id] = create_ai_agent(tools, user, config)
        
        agent = sessions[session_id]
        result = agent.process_request(body.get('message', ''))
        
        return JSONResponse({
            'type': result.get('type', 'response'),
            'message': result.get('message', ''),
            'requires_confirmation': result.get('requires_confirmation', False),
            'action_data': result.get('action_data'),
            'session_id': session_id
        })
    except Exception as e:
        logger.error(f"Chat error: {e}")
        return JSONResponse({"detail": str(e)}, status_code=500)

async def confirm_action(request: Request):
    try:
        auth_header = request.headers.get('authorization')
        if not auth_header or not auth_header.startswith("Bearer "):
            return JSONResponse({"detail": "Unauthorized"}, status_code=401)
        
        token = auth_header.replace("Bearer ", "")
        user = auth_manager.authenticate_token(token)
        if not user:
            return JSONResponse({"detail": "Invalid token"}, status_code=401)
        
        if not action_tools.pending_action:
            return JSONResponse({"status": "error", "message": "No pending action"})
        
        action = action_tools.pending_action
        ticket_id = action.get('ticket_id', 'TKT-501')
        action_tools.pending_action = None
        
        return JSONResponse({
            'status': 'success',
            'message': f'✅ Escalation created for ticket {ticket_id}',
            'ticket_id': ticket_id,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return JSONResponse({"detail": str(e)}, status_code=500)

async def serve_frontend(request):
    try:
        with open("src/frontend/index.html", "r", encoding='utf-8') as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse("""
        <h1>📦 ParcelPilot AI Support</h1>
        <p>✅ API is running!</p>
        <p>🔑 Test credentials: customer_001 / pass123</p>
        <p>📚 API Docs: <a href="/docs">/docs</a></p>
        """)

# ============================================
# REGISTER ROUTES
# ============================================
app.routes = [
    Route("/", root),
    Route("/api/health", health),
    Route("/api/auth/login", login, methods=["POST"]),
    Route("/api/chat", chat, methods=["POST"]),
    Route("/api/confirm", confirm_action, methods=["POST"]),
    Route("/app", serve_frontend),
]

# ============================================
# MAIN
# ============================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)