"""
Authentication module for handling RS256 JWTs.
"""

import jwt
from datetime import datetime, timedelta
from typing import Optional
import secrets

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.config import settings
from app.utils import security_logger

def create_access_token(data: dict) -> str:
    """
    Generates a signed RS256 JWT using the private key.

    Args:
        data (dict): The payload to encode into the JWT.

    Returns:
        str: The signed JWT string.
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    
    # Sign with the PRIVATE key from config
    encoded_jwt = jwt.encode(to_encode, settings.JWT_PRIVATE_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> Optional[dict]:
    """
    Verifies a token using the public key.

    Args:
        token (str): The JWT string to verify.

    Returns:
        Optional[dict]: The decoded payload if valid, None if expired or tampered with.
    """
    try:
        # Verify with the PUBLIC key from config
        payload = jwt.decode(token, settings.JWT_PUBLIC_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None  # Token expired
    except jwt.InvalidTokenError:
        return None  # Token tampered with or invalid


# ── FastAPI Dependency: JWT Bearer Auth ──────────────────────────────
_bearer_scheme = HTTPBearer(auto_error=False)

async def require_token(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
) -> dict:
    """
    FastAPI dependency that enforces a valid JWT Bearer token.
    Returns the decoded payload on success; raises 401 otherwise.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = verify_token(credentials.credentials)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload


# ── FastAPI Dependency: Admin Secret Key Auth ────────────────────────
async def require_admin(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
) -> bool:
    """
    FastAPI dependency that enforces the admin secret key.
    The client must send: Authorization: Bearer <ADMIN_SECRET_KEY>
    Returns True on success; raises 403 otherwise.
    """
    client_ip = request.client.host if request.client else "Unknown"
    
    if credentials is None:
        security_logger.log_event("ADMIN_AUTH_FAILED", "WARNING", client_ip, "Missing admin credentials.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing admin credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # Constant-time comparison to prevent timing attacks
    if not secrets.compare_digest(credentials.credentials, settings.ADMIN_SECRET_KEY):
        security_logger.log_event("ADMIN_AUTH_FAILED", "CRITICAL", client_ip, "Invalid admin credentials (Timing attack protection active).")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin credentials.",
        )
    return True

async def require_admin_jwt(
    payload: dict = Depends(require_token),
) -> dict:
    """
    FastAPI dependency that enforces a valid JWT Bearer token AND an admin role.
    Returns the decoded payload on success; raises 403 otherwise.
    """
    if payload.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required.",
        )
    return payload
