# src/auth/auth_manager.py
from enum import Enum
from typing import Optional, Dict, Any
from dataclasses import dataclass
import jwt
import hashlib
import json
from datetime import datetime, timedelta

class UserRole(Enum):
    CUSTOMER = "customer"
    SUPPORT_AGENT = "support_agent"
    OPS_MANAGER = "ops_manager"
    ADMIN = "admin"

@dataclass
class User:
    user_id: str
    role: UserRole
    account_id: Optional[str] = None
    permissions: list = None
    
    def __post_init__(self):
        if self.permissions is None:
            self.permissions = self.get_default_permissions()
    
    def get_default_permissions(self) -> list:
        """Get default permissions based on role"""
        permissions_map = {
            UserRole.CUSTOMER: [
                "view_own_account",
                "view_own_orders",
                "view_own_tickets",
                "create_ticket"
            ],
            UserRole.SUPPORT_AGENT: [
                "view_all_accounts",
                "view_all_orders",
                "view_all_tickets",
                "update_ticket",
                "create_escalation",
                "view_own_account"
            ],
            UserRole.OPS_MANAGER: [
                "view_all_accounts",
                "view_all_orders",
                "view_all_tickets",
                "update_ticket",
                "create_escalation",
                "view_monitoring",
                "view_analytics",
                "manage_team"
            ],
            UserRole.ADMIN: [
                "*"  # All permissions
            ]
        }
        return permissions_map.get(self.role, [])
    
    def can_access_account(self, account_id: str) -> bool:
        """Check if user can access a specific account"""
        if self.role == UserRole.ADMIN:
            return True
        elif self.role in [UserRole.SUPPORT_AGENT, UserRole.OPS_MANAGER]:
            return True
        elif self.role == UserRole.CUSTOMER:
            return self.account_id == account_id
        return False
    
    def has_permission(self, permission: str) -> bool:
        """Check if user has a specific permission"""
        if "*" in self.permissions:
            return True
        return permission in self.permissions

class AuthManager:
    def __init__(self, config: Dict):
        self.config = config
        self.secret_key = config.get('SECRET_KEY', 'dev_secret_key')
        
        # Mock user database (in production, use real DB)
# src/auth/auth_manager.py - Fix account IDs

        self.users = {
            "customer_001": {
                "role": UserRole.CUSTOMER,
                "account_id": "ACCT-001",  # ← FIXED: Was "ACC-001"
                "password": self.hash_password("pass123")
            },
            "customer_002": {
                "role": UserRole.CUSTOMER,
                "account_id": "ACCT-002",  # ← FIXED: Was "ACC-002"
                "password": self.hash_password("pass123")
            },
            "support_001": {
                "role": UserRole.SUPPORT_AGENT,
                "account_id": None,
                "password": self.hash_password("support123")
            },
            "ops_001": {
                "role": UserRole.OPS_MANAGER,
                "account_id": None,
                "password": self.hash_password("ops123")
            },
            "admin_001": {
                "role": UserRole.ADMIN,
                "account_id": None,
                "password": self.hash_password("admin123")
            }
        }
    
    def hash_password(self, password: str) -> str:
        """Hash password for storage"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def authenticate(self, user_id: str, password: str) -> Optional[User]:
        """Authenticate user with user_id and password"""
        if user_id not in self.users:
            return None
        
        user_data = self.users[user_id]
        
        # In production, use proper password verification
        if user_data["password"] != self.hash_password(password):
            return None
        
        return User(
            user_id=user_id,
            role=user_data["role"],
            account_id=user_data.get("account_id")
        )
    
    def authenticate_token(self, token: str) -> Optional[User]:
        """Authenticate using JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            user_id = payload.get('user_id')
            
            if user_id not in self.users:
                return None
            
            user_data = self.users[user_id]
            return User(
                user_id=user_id,
                role=user_data["role"],
                account_id=user_data.get("account_id")
            )
        except jwt.InvalidTokenError:
            return None
    
    def generate_token(self, user: User) -> str:
        """Generate JWT token for authenticated user"""
        payload = {
            'user_id': user.user_id,
            'role': user.role.value,
            'account_id': user.account_id,
            'exp': datetime.utcnow() + timedelta(hours=24)
        }
        return jwt.encode(payload, self.secret_key, algorithm='HS256')
    
    def create_user(self, user_id: str, role: UserRole, 
                   account_id: Optional[str] = None, 
                   password: str = "default123") -> User:
        """Create a new user (for testing)"""
        self.users[user_id] = {
            "role": role,
            "account_id": account_id,
            "password": self.hash_password(password)
        }
        return User(user_id=user_id, role=role, account_id=account_id)