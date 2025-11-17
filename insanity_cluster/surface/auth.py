"""
Authentication and session management for SURFACE layer.

Implements API key and JWT validation, role-based access control (RBAC),
and session management with Redis.
"""
import hashlib
import secrets
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from enum import Enum

import jwt
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader, HTTPBearer, HTTPAuthorizationCredentials

from insanity_cluster.common.config import settings
from insanity_cluster.table.redis_manager import RedisManager
from insanity_cluster.table.database import DatabaseManager
from insanity_cluster.table.models import User

logger = logging.getLogger(__name__)


class UserRole(str, Enum):
    """User roles for RBAC"""
    ADMIN = "admin"
    USER = "user"
    READONLY = "readonly"


class AuthenticationError(Exception):
    """Raised when authentication fails"""
    pass


class AuthorizationError(Exception):
    """Raised when authorization fails"""
    pass


# Security schemes
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)


class AuthManager:
    """
    Manages authentication and authorization.
    
    Supports both API key and JWT token authentication with Redis-based
    session management and role-based access control.
    """
    
    def __init__(
        self,
        db_manager: DatabaseManager,
        redis_manager: RedisManager
    ):
        """
        Initialize auth manager.
        
        Args:
            db_manager: Database manager for user lookups
            redis_manager: Redis manager for session storage
        """
        self.db_manager = db_manager
        self.redis_manager = redis_manager
        self.secret_key = settings.api_secret_key
        self.algorithm = settings.jwt_algorithm
        self.token_expiration = timedelta(hours=settings.jwt_expiration_hours)
        self.session_ttl = settings.jwt_expiration_hours * 3600  # Convert to seconds
        
        logger.info("AuthManager initialized")
    
    def generate_api_key(self) -> tuple[str, str]:
        """
        Generate a new API key.
        
        Returns:
            Tuple of (api_key, api_key_hash)
        """
        # Generate a secure random API key
        api_key = f"ic_{secrets.token_urlsafe(32)}"
        api_key_hash = self._hash_api_key(api_key)
        
        logger.info("Generated new API key")
        return api_key, api_key_hash
    
    def rotate_api_key(self, user_id: str) -> str:
        """
        Rotate API key for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            New API key
        """
        api_key, api_key_hash = self.generate_api_key()
        
        # Update user's API key in database
        with self.db_manager.get_session() as session:
            user = session.query(User).filter(User.id == user_id).first()
            if not user:
                raise AuthenticationError(f"User {user_id} not found")
            
            user.api_key_hash = api_key_hash
            session.commit()
        
        logger.info(f"Rotated API key for user {user_id}")
        return api_key
    
    async def verify_api_key(self, api_key: str) -> User:
        """
        Verify API key and return user.
        
        Args:
            api_key: API key to verify
            
        Returns:
            User object
            
        Raises:
            AuthenticationError: If API key is invalid
        """
        if not api_key:
            raise AuthenticationError("API key is required")
        
        api_key_hash = self._hash_api_key(api_key)
        
        # Look up user by API key hash
        with self.db_manager.get_session() as session:
            user = session.query(User).filter(
                User.api_key_hash == api_key_hash
            ).first()
            
            if not user:
                logger.warning(f"Invalid API key attempt")
                raise AuthenticationError("Invalid API key")
            
            logger.info(f"API key verified for user {user.id}")
            return user
    
    def create_jwt_token(self, user_id: str, role: str) -> str:
        """
        Create JWT token for user.
        
        Args:
            user_id: User ID
            role: User role
            
        Returns:
            JWT token string
        """
        now = datetime.utcnow()
        expires = now + self.token_expiration
        
        payload = {
            "sub": user_id,
            "role": role,
            "iat": now,
            "exp": expires
        }
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        
        logger.info(f"Created JWT token for user {user_id}")
        return token
    
    async def verify_jwt_token(self, token: str) -> Dict[str, Any]:
        """
        Verify JWT token and return payload.
        
        Args:
            token: JWT token string
            
        Returns:
            Token payload
            
        Raises:
            AuthenticationError: If token is invalid or expired
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
            
            user_id = payload.get("sub")
            if not user_id:
                raise AuthenticationError("Invalid token payload")
            
            logger.info(f"JWT token verified for user {user_id}")
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.warning("Expired JWT token")
            raise AuthenticationError("Token has expired")
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {e}")
            raise AuthenticationError("Invalid token")
    
    async def create_session(self, user_id: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Create user session in Redis.
        
        Args:
            user_id: User ID
            metadata: Optional session metadata
            
        Returns:
            Session ID
        """
        session_id = secrets.token_urlsafe(32)
        
        session_data = {
            "user_id": user_id,
            "created_at": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        }
        
        # Store session in Redis
        session_key = f"session:{session_id}"
        self.redis_manager.setex(
            session_key,
            self.session_ttl,
            str(session_data)
        )
        
        # Also store user's active sessions
        user_sessions_key = f"user_sessions:{user_id}"
        self.redis_manager.sadd(user_sessions_key, session_id)
        self.redis_manager.expire(user_sessions_key, self.session_ttl)
        
        logger.info(f"Created session {session_id} for user {user_id}")
        return session_id
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session data from Redis.
        
        Args:
            session_id: Session ID
            
        Returns:
            Session data or None if not found
        """
        session_key = f"session:{session_id}"
        session_data = self.redis_manager.get(session_key)
        
        if session_data:
            # Refresh session TTL
            self.redis_manager.expire(session_key, self.session_ttl)
            return eval(session_data)  # Convert string back to dict
        
        return None
    
    async def delete_session(self, session_id: str) -> None:
        """
        Delete session from Redis.
        
        Args:
            session_id: Session ID
        """
        session_key = f"session:{session_id}"
        session_data = await self.get_session(session_id)
        
        if session_data:
            user_id = session_data.get("user_id")
            if user_id:
                user_sessions_key = f"user_sessions:{user_id}"
                self.redis_manager.srem(user_sessions_key, session_id)
        
        self.redis_manager.delete(session_key)
        logger.info(f"Deleted session {session_id}")
    
    async def delete_user_sessions(self, user_id: str) -> None:
        """
        Delete all sessions for a user.
        
        Args:
            user_id: User ID
        """
        user_sessions_key = f"user_sessions:{user_id}"
        session_ids = self.redis_manager.smembers(user_sessions_key)
        
        for session_id in session_ids:
            session_key = f"session:{session_id}"
            self.redis_manager.delete(session_key)
        
        self.redis_manager.delete(user_sessions_key)
        logger.info(f"Deleted all sessions for user {user_id}")
    
    def check_permission(self, user_role: str, required_role: UserRole) -> bool:
        """
        Check if user has required permission.
        
        Args:
            user_role: User's role
            required_role: Required role
            
        Returns:
            True if user has permission
        """
        role_hierarchy = {
            UserRole.READONLY: 0,
            UserRole.USER: 1,
            UserRole.ADMIN: 2
        }
        
        user_level = role_hierarchy.get(UserRole(user_role), -1)
        required_level = role_hierarchy.get(required_role, 999)
        
        return user_level >= required_level
    
    def require_role(self, user_role: str, required_role: UserRole) -> None:
        """
        Require user to have specific role.
        
        Args:
            user_role: User's role
            required_role: Required role
            
        Raises:
            AuthorizationError: If user doesn't have required role
        """
        if not self.check_permission(user_role, required_role):
            raise AuthorizationError(
                f"Required role: {required_role.value}, user role: {user_role}"
            )
    
    def _hash_api_key(self, api_key: str) -> str:
        """Hash API key for storage"""
        return hashlib.sha256(api_key.encode()).hexdigest()


# Dependency functions for FastAPI
async def get_current_user_api_key(
    api_key: Optional[str] = Security(api_key_header)
) -> User:
    """
    FastAPI dependency to get current user from API key.
    
    Args:
        api_key: API key from header
        
    Returns:
        User object
        
    Raises:
        HTTPException: If authentication fails
    """
    # Note: In production, auth_manager should be injected via app state
    # For now, we'll create a minimal user object for testing
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is required",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    try:
        user = await auth_manager.verify_api_key(api_key)
        return user
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "ApiKey"},
        )


async def get_current_user_jwt(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme)
) -> Dict[str, Any]:
    """
    FastAPI dependency to get current user from JWT token.
    
    Args:
        credentials: Bearer token credentials
        auth_manager: Auth manager instance
        
    Returns:
        Token payload with user info
        
    Raises:
        HTTPException: If authentication fails
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token is required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        payload = await auth_manager.verify_jwt_token(credentials.credentials)
        return payload
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_role_dependency(required_role: UserRole):
    """
    Create a FastAPI dependency that requires a specific role.
    
    Args:
        required_role: Required role
        
    Returns:
        Dependency function
    """
    async def role_checker(
        user: User = Security(get_current_user_api_key)
    ) -> User:
        auth_manager = AuthManager(None, None)  # Will be injected properly
        try:
            auth_manager.require_role(user.role, required_role)
            return user
        except AuthorizationError as e:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(e)
            )
    
    return role_checker
