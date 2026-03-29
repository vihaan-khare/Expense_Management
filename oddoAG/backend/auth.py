"""JWT authentication helpers and route decorators."""

import jwt
import secrets
from datetime import datetime, timedelta, timezone
from functools import wraps
from flask import request, jsonify, g
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config


def hash_password(password):
    """Hash a password using Werkzeug's secure hashing."""
    return generate_password_hash(password, method="pbkdf2:sha256", salt_length=16)


def verify_password(password, password_hash):
    """Verify a password against its hash."""
    return check_password_hash(password_hash, password)


def create_token(user_id, company_id, role):
    """Create a JWT token with user info."""
    payload = {
        "user_id": user_id,
        "company_id": company_id,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(hours=Config.JWT_EXPIRY_HOURS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, Config.JWT_SECRET, algorithm="HS256")


def decode_token(token):
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(token, Config.JWT_SECRET, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def generate_invite_token():
    """Generate a secure random invite token."""
    return secrets.token_urlsafe(48)


def login_required(f):
    """Decorator to require authentication on a route."""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.cookies.get("auth_token")
        if not token:
            # Also check Authorization header for API flexibility
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                token = auth_header[7:]

        if not token:
            return jsonify({"error": "Authentication required"}), 401

        payload = decode_token(token)
        if not payload:
            return jsonify({"error": "Invalid or expired token"}), 401

        # Store user info in Flask's g object for the request
        g.user_id = payload["user_id"]
        g.company_id = payload["company_id"]
        g.role = payload["role"]

        return f(*args, **kwargs)
    return decorated


def role_required(*roles):
    """Decorator to require specific role(s). Must be used after @login_required."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if g.role not in roles:
                return jsonify({"error": "Insufficient permissions"}), 403
            return f(*args, **kwargs)
        return decorated
    return decorator


def set_auth_cookie(response, token):
    """Set the JWT token as an httpOnly cookie on the response."""
    response.set_cookie(
        "auth_token",
        token,
        httponly=True,
        secure=False,  # Set to True in production with HTTPS
        samesite="Lax",
        max_age=Config.JWT_EXPIRY_HOURS * 3600,
        path="/",
    )
    return response


def clear_auth_cookie(response):
    """Clear the auth cookie."""
    response.delete_cookie("auth_token", path="/")
    return response
