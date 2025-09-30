"""Authentication and authorization module for OSAA MVP.

This module provides secure authentication and authorization for the application,
including password protection, session management, and role-based access control.
"""

import os
import hashlib
import secrets
import time
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import jwt
from functools import wraps
import logging

from pipeline.exceptions import AuthenticationError, AuthorizationError

logger = logging.getLogger(__name__)

# Configuration
SECRET_KEY = os.getenv('APP_SECRET_KEY', secrets.token_urlsafe(32))
SESSION_TIMEOUT = int(os.getenv('SESSION_TIMEOUT_MINUTES', '480'))  # 8 hours default
MAX_LOGIN_ATTEMPTS = int(os.getenv('MAX_LOGIN_ATTEMPTS', '5'))
LOCKOUT_DURATION = int(os.getenv('LOCKOUT_DURATION_MINUTES', '30'))

# In-memory session store (in production, use Redis or database)
sessions: Dict[str, Dict[str, Any]] = {}
login_attempts: Dict[str, Dict[str, Any]] = {}

# Default admin credentials (should be changed in production)
DEFAULT_ADMIN_USER = os.getenv('ADMIN_USERNAME', 'admin')
DEFAULT_ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'ChangeThisPassword123!')

def hash_password(password: str) -> str:
    """Hash password using SHA-256 with salt."""
    salt = secrets.token_hex(16)
    password_hash = hashlib.pbkdf2_hmac('sha256', 
                                       password.encode('utf-8'), 
                                       salt.encode('utf-8'), 
                                       100000)
    return f"{salt}:{password_hash.hex()}"

def verify_password(password: str, hashed_password: str) -> bool:
    """Verify password against hash."""
    try:
        salt, stored_hash = hashed_password.split(':')
        password_hash = hashlib.pbkdf2_hmac('sha256',
                                           password.encode('utf-8'),
                                           salt.encode('utf-8'),
                                           100000)
        return password_hash.hex() == stored_hash
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False

def check_login_attempts(username: str, ip_address: str) -> bool:
    """Check if user is locked out due to too many failed attempts."""
    key = f"{username}:{ip_address}"
    now = time.time()
    
    if key in login_attempts:
        attempts_info = login_attempts[key]
        
        # Check if still locked out
        if now - attempts_info['last_attempt'] < (LOCKOUT_DURATION * 60):
            if attempts_info['count'] >= MAX_LOGIN_ATTEMPTS:
                logger.warning(f"User {username} from {ip_address} is locked out")
                return False
    
    return True

def record_login_attempt(username: str, ip_address: str, success: bool):
    """Record login attempt for security monitoring."""
    key = f"{username}:{ip_address}"
    now = time.time()
    
    if success:
        # Clear failed attempts on successful login
        if key in login_attempts:
            del login_attempts[key]
    else:
        # Record failed attempt
        if key not in login_attempts:
            login_attempts[key] = {'count': 0, 'last_attempt': now}
        
        login_attempts[key]['count'] += 1
        login_attempts[key]['last_attempt'] = now

def create_session(username: str, ip_address: str) -> str:
    """Create a new user session."""
    session_id = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(minutes=SESSION_TIMEOUT)
    
    # Create JWT token
    payload = {
        'username': username,
        'session_id': session_id,
        'ip_address': ip_address,
        'exp': expires_at,
        'iat': datetime.utcnow()
    }
    
    token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
    
    # Store session
    sessions[session_id] = {
        'username': username,
        'ip_address': ip_address,
        'created_at': datetime.utcnow(),
        'expires_at': expires_at,
        'last_activity': datetime.utcnow()
    }
    
    logger.info(f"Session created for user {username} from {ip_address}")
    return token

def validate_session(token: str, ip_address: str) -> Optional[Dict[str, Any]]:
    """Validate session token and return user info."""
    try:
        # Decode JWT token
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        
        session_id = payload.get('session_id')
        username = payload.get('username')
        
        if not session_id or not username:
            return None
        
        # Check if session exists and is valid
        if session_id not in sessions:
            return None
        
        session = sessions[session_id]
        
        # Check IP address
        if session['ip_address'] != ip_address:
            logger.warning(f"IP address mismatch for session {session_id}")
            return None
        
        # Check expiration
        if datetime.utcnow() > session['expires_at']:
            del sessions[session_id]
            return None
        
        # Update last activity
        session['last_activity'] = datetime.utcnow()
        
        return {
            'username': username,
            'session_id': session_id,
            'expires_at': session['expires_at']
        }
    
    except jwt.ExpiredSignatureError:
        logger.info("Session token expired")
        return None
    except jwt.InvalidTokenError:
        logger.warning("Invalid session token")
        return None
    except Exception as e:
        logger.error(f"Session validation error: {e}")
        return None

def authenticate_user(username: str, password: str, ip_address: str) -> Optional[str]:
    """Authenticate user and return session token."""
    # Check login attempts
    if not check_login_attempts(username, ip_address):
        raise AuthenticationError("Account temporarily locked due to too many failed attempts")
    
    # For now, use default admin credentials
    # In production, this should check against a database
    if username == DEFAULT_ADMIN_USER:
        # Hash the default password for comparison
        hashed_default = hash_password(DEFAULT_ADMIN_PASSWORD)
        if verify_password(password, hashed_default):
            record_login_attempt(username, ip_address, True)
            return create_session(username, ip_address)
    
    # Record failed attempt
    record_login_attempt(username, ip_address, False)
    raise AuthenticationError("Invalid username or password")

def logout_user(session_id: str):
    """Logout user and invalidate session."""
    if session_id in sessions:
        username = sessions[session_id]['username']
        del sessions[session_id]
        logger.info(f"User {username} logged out")

def cleanup_expired_sessions():
    """Clean up expired sessions."""
    now = datetime.utcnow()
    expired_sessions = [
        session_id for session_id, session in sessions.items()
        if now > session['expires_at']
    ]
    
    for session_id in expired_sessions:
        del sessions[session_id]
    
    if expired_sessions:
        logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")

def require_auth(func):
    """Decorator to require authentication for functions."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        # This would be implemented in the web interface
        # For now, we'll just log the requirement
        logger.info(f"Authentication required for {func.__name__}")
        return func(*args, **kwargs)
    return wrapper

def require_admin(func):
    """Decorator to require admin privileges for functions."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        # This would check user roles in the web interface
        logger.info(f"Admin privileges required for {func.__name__}")
        return func(*args, **kwargs)
    return wrapper

def get_security_status() -> Dict[str, Any]:
    """Get current security status and statistics."""
    active_sessions = len([s for s in sessions.values() 
                          if datetime.utcnow() < s['expires_at']])
    
    failed_attempts = sum(info['count'] for info in login_attempts.values())
    
    return {
        'active_sessions': active_sessions,
        'total_sessions': len(sessions),
        'failed_login_attempts': failed_attempts,
        'locked_accounts': len([k for k, v in login_attempts.items() 
                               if v['count'] >= MAX_LOGIN_ATTEMPTS]),
        'session_timeout_minutes': SESSION_TIMEOUT,
        'max_login_attempts': MAX_LOGIN_ATTEMPTS,
        'lockout_duration_minutes': LOCKOUT_DURATION
    }
