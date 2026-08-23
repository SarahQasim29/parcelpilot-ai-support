// src/frontend/scripts.js
// State
let sessionId = null;
let token = null;
let currentUser = null;
let pendingActionId = null;
let isProcessing = false;

// DOM Elements
const chatMessages = document.getElementById('chatMessages');
const messageInput = document.getElementById('messageInput');
const sendButton = document.getElementById('sendButton');
const chatStatus = document.getElementById('chatStatus');
const userBadge = document.getElementById('userBadge');
const loginModal = document.getElementById('loginModal');

// Initialize
document.addEventListener('DOMContentLoaded', function() {
    checkAuth();
    setupLoginForm();
    startAlertPolling();
});

// Authentication
function checkAuth() {
    token = localStorage.getItem('token');
    if (token) {
        // Validate token and get user info
        fetchUserInfo();
        loginModal.style.display = 'none';
    } else {
        loginModal.style.display = 'flex';
    }
}

function setupLoginForm() {
    document.getElementById('loginForm').addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const userId = document.getElementById('userId').value;
        const password = document.getElementById('password').value;
        
        try {
            const response = await fetch('/api/auth/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ user_id: userId, password })
            });
            
            if (!response.ok) {
                throw new Error('Login failed');
            }
            
            const data = await response.json();
            token = data.token;
            currentUser = data;
            
            localStorage.setItem('token', token);
            localStorage.setItem('user', JSON.stringify(currentUser));
            
            updateUserInfo();
            loginModal.style.display = 'none';
            addMessage('System', `Logged in as ${data.role}`, 'assistant');
            
        } catch (error) {
            alert(`Login failed: ${error.message}`);
        }
    });
}

async function fetchUserInfo() {
    try {
        // Get user info from token
        const userData = localStorage.getItem('user');
        if (userData) {
            currentUser = JSON.parse(userData);
            updateUserInfo();
        }
    } catch (error) {
        console.error('Error fetching user info:', error);
        logout();
    }
}

function updateUserInfo() {
    if (currentUser) {
        userBadge.textContent = `${currentUser.role} (${currentUser.user_id})`;
    }
}

function logout() {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    token = null;
    currentUser = null;
    sessionId = null;
    loginModal.style.display = 'flex';
    chatMessages.innerHTML = '';
    addMessage('System', 'Logged out successfully', 'assistant');
}

// Chat Functions
async function sendMessage() {
    const message = messageInput.value.trim();
    if (!message || isProcessing || !token) return;
    
    isProcessing = true;
    sendButton.disabled = true;
    messageInput.disabled = true;
    chatStatus.textContent = 'Processing...';
    
    // Add user message
    addMessage('You', message, 'user');
    messageInput.value = '';
    
    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                message: message,
                session_id: sessionId
            })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Request failed');
        }
        
        const data = await response.json();
        sessionId = data.session_id;
        
        handleChatResponse(data);
        
    } catch (error) {
        console.error('Chat error:', error);
        addMessage('System', `Error: ${error.message}`, 'error');
        chatStatus.textContent = 'Error occurred';
    } finally {
        isProcessing = false;
        sendButton.disabled = false;
        messageInput.disabled = false;
        messageInput.focus();
        chatStatus.textContent = 'Ready';
    }
}

function handleChatResponse(data) {
    switch(data.type) {
        case 'response':
            addMessage('Assistant', data.message, 'assistant');
            break;
            
        case 'action_required':
            addMessage('Assistant', data.message, 'confirmation');
            pendingActionId = data.action_data?.action_id;
            if (pendingActionId) {
                addConfirmationButtons();
            }
            break;
            
        case 'error':
            addMessage('System', data.message, 'error');
            break;
            
        case 'confirmation':
            addMessage('Assistant', data.message, 'assistant');
            break;
            
        default:
            addMessage('Assistant', data.message, 'assistant');
    }
}

function addMessage(sender, content, type = 'assistant') {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}`;
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.textContent = content;
    
    messageDiv.appendChild(contentDiv);
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function addConfirmationButtons() {
    const container = document.createElement('div');
    container.className = 'confirmation-actions';
    
    const confirmBtn = document.createElement('button');
    confirmBtn.className = 'confirm-btn';
    confirmBtn.textContent = 'Confirm';
    confirmBtn.onclick = confirmAction;
    
    const cancelBtn = document.createElement('button');
    cancelBtn.className = 'cancel-btn';
    cancelBtn.textContent = 'Cancel';
    cancelBtn.onclick = cancelAction;
    
    container.appendChild(confirmBtn);
    container.appendChild(cancelBtn);
    
    const lastMessage = chatMessages.lastElementChild;
    lastMessage.appendChild(container);
}

async function confirmAction() {
    if (!pendingActionId || !sessionId) return;
    
    try {
        const response = await fetch('/api/confirm', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                session_id: sessionId,
                action_id: pendingActionId,
                confirm: true
            })
        });
        
        if (!response.ok) {
            throw new Error('Confirmation failed');
        }
        
        const data = await response.json();
        addMessage('Assistant', data.message || 'Action confirmed and executed', 'assistant');
        pendingActionId = null;
        
        // Remove confirmation buttons
        const confirmBtns = document.querySelectorAll('.confirmation-actions');
        confirmBtns.forEach(el => el.remove());
        
    } catch (error) {
        console.error('Confirmation error:', error);
        addMessage('System', `Error: ${error.message}`, 'error');
    }
}

async function cancelAction() {
    if (!pendingActionId || !sessionId) return;
    
    try {
        const response = await fetch('/api/confirm', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                session_id: sessionId,
                action_id: pendingActionId,
                confirm: false
            })
        });
        
        const data = await response.json();
        addMessage('Assistant', 'Action cancelled', 'assistant');
        pendingActionId = null;
        
        // Remove confirmation buttons
        const confirmBtns = document.querySelectorAll('.confirmation-actions');
        confirmBtns.forEach(el => el.remove());
        
    } catch (error) {
        console.error('Cancel error:', error);
    }
}

// Keypress handler
function handleKeyPress(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
}

// Alert Polling (for Ops users)
async function startAlertPolling() {
    setInterval(async () => {
        if (currentUser && (currentUser.role === 'ops_manager' || currentUser.role === 'admin')) {
            await fetchAlerts();
        }
    }, 30000); // Every 30 seconds
}

async function fetchAlerts() {
    try {
        const response = await fetch('/api/alerts', {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (response.ok) {
            const alerts = await response.json();
            updateAlertsDisplay(alerts);
        }
    } catch (error) {
        console.error('Error fetching alerts:', error);
    }
}

function updateAlertsDisplay(alerts) {
    const container = document.getElementById('alertsContainer');
    container.innerHTML = '';
    
    if (!alerts || alerts.length === 0) {
        container.innerHTML = '<p style="color: #6b7280; font-size: 13px;">No active alerts</p>';
        return;
    }
    
    alerts.forEach(alert => {
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert-item ${alert.severity}`;
        alertDiv.innerHTML = `
            <div class="alert-title">${alert.type.replace('_', ' ').toUpperCase()}</div>
            <div class="alert-description">${alert.description}</div>
            <div style="font-size: 11px; color: #9e9e9e; margin-top: 4px;">
                ${alert.affected_accounts?.length || 0} accounts affected
            </div>
        `;
        container.appendChild(alertDiv);
    });
}

// Add tool usage indicator
function showToolUsage(toolName) {
    const indicators = document.getElementById('toolIndicators');
    const toolDiv = document.createElement('div');
    toolDiv.className = 'tool-indicator active';
    toolDiv.innerHTML = `
        <span class="tool-icon">🔧</span>
        <span>Using: ${toolName}</span>
    `;
    indicators.appendChild(toolDiv);
    
    // Remove after 3 seconds
    setTimeout(() => {
        toolDiv.remove();
    }, 3000);
}