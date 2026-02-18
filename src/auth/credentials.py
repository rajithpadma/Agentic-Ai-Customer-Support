"""
Credentials Module for Agentic AI Customer Support
Handles user authentication and session management
"""
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src.database.database import db_manager


class CredentialsManager:
    """Manages user credentials and authentication"""
    
    def __init__(self):
        self.active_sessions: Dict[str, Dict] = {}
        self.session_timeout = timedelta(hours=24)
    
    def extract_user_id(self, identifier: str) -> Optional[str]:
        """
        Extract user ID from various identifiers (email, phone, username)
        Returns the user_id if found
        """
        user = db_manager.get_user_by_id(identifier)
        if user:
            return user.get("user_id", identifier)
        return identifier  # Return as-is if not found
    
    def authenticate(self, user_id: str, password: str = None) -> Dict:
        """
        Authenticate user and create session
        Returns session data if successful
        Note: Simplified authentication for demo
        """
        # Get user info from database
        user = db_manager.get_user_by_id(user_id)
        
        # Create session
        session_id = self._generate_session_id()
        session_data = {
            "session_id": session_id,
            "user_id": user.get("user_id", user_id) if user else user_id,
            "user_name": user.get("name", "Customer") if user else "Customer",
            "email": user.get("email", "") if user else "",
            "created_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + self.session_timeout,
            "is_authenticated": True
        }
        
        self.active_sessions[session_id] = session_data
        
        return {
            "success": True,
            "session": session_data,
            "user": user if user else {"user_id": user_id, "name": "Customer"}
        }
    
    def validate_session(self, session_id: str) -> Dict:
        """Validate if a session is still active"""
        session = self.active_sessions.get(session_id)
        
        if not session:
            return {"valid": False, "error": "Session not found"}
        
        if datetime.utcnow() > session.get("expires_at"):
            del self.active_sessions[session_id]
            return {"valid": False, "error": "Session expired"}
        
        return {
            "valid": True,
            "session": session
        }
    
    def get_user_from_session(self, session_id: str) -> Optional[Dict]:
        """Get user details from session"""
        validation = self.validate_session(session_id)
        
        if validation.get("valid"):
            user_id = validation["session"].get("user_id")
            return db_manager.get_user_by_id(user_id)
        
        return None
    
    def logout(self, session_id: str) -> bool:
        """End user session"""
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
            return True
        return False
    
    def create_guest_session(self) -> Dict:
        """Create a guest session for unauthenticated users"""
        session_id = self._generate_session_id()
        session_data = {
            "session_id": session_id,
            "user_id": None,
            "user_name": "Guest",
            "is_authenticated": False,
            "created_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(hours=1)
        }
        
        self.active_sessions[session_id] = session_data
        return session_data
    
    def _generate_session_id(self) -> str:
        """Generate a secure session ID"""
        return secrets.token_urlsafe(32)


# Create singleton instance
credentials_manager = CredentialsManager()
