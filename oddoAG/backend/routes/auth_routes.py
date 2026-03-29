"""Authentication routes — signup, login, logout, invite acceptance."""

from datetime import datetime, timedelta, timezone
from flask import Blueprint, request, jsonify, make_response, g
from sqlalchemy.exc import IntegrityError
from backend.database import db_session
from backend.models import Company, User
from backend.auth import (
    hash_password, verify_password, create_token, generate_invite_token,
    login_required, set_auth_cookie, clear_auth_cookie
)

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


import random
import string

@auth_bp.route("/signup", methods=["POST"])
def signup():
    """Create a new company/admin OR join existing via company_code."""
    data = request.get_json()

    # Determine role
    role = data.get("role", "employee").strip().lower()
    if role not in ("admin", "manager", "employee"):
        return jsonify({"error": "Invalid role"}), 400

    # Validate required fields
    required = ["name", "email", "password"]
    if role == "admin":
        required.extend(["company_name", "country", "currency_code"])
    else:
        required.append("company_code")

    for field in required:
        if not data.get(field, ""):  # Can't use .strip() directly if somehow not a string, but assume strings based on current UI
            if isinstance(data.get(field), str) and not data[field].strip():
                return jsonify({"error": f"{field} is required"}), 400
            elif not data.get(field):
                return jsonify({"error": f"{field} is required"}), 400

    if len(data["password"]) < 8:
        return jsonify({"error": "Password must be at least 8 characters"}), 400

    session = db_session()
    try:
        # Check if email already exists
        existing = session.query(User).filter_by(email=data["email"].lower().strip()).first()
        if existing:
            return jsonify({"error": "Email already registered"}), 409

        if role == "admin":
            # Generate unique code and create company
            company_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            company = Company(
                name=data["company_name"].strip(),
                country=data["country"].strip(),
                currency_code=data["currency_code"].strip().upper(),
                company_code=company_code
            )
            session.add(company)
            session.flush()  # Get company.id
        else:
            # Find company by code
            code = data["company_code"].strip().upper()
            company = session.query(Company).filter_by(company_code=code).first()
            if not company:
                return jsonify({"error": "Invalid Company Code"}), 404

        # Create user
        user = User(
            company_id=company.id,
            name=data["name"].strip(),
            email=data["email"].lower().strip(),
            password_hash=hash_password(data["password"]),
            role=role,
            invite_status="active",
        )
        session.add(user)
        session.commit()

        # Create token and set cookie
        token = create_token(user.id, company.id, role)
        response = make_response(jsonify({
            "message": "Account created successfully",
            "user": user.to_dict(),
            "company": company.to_dict(),
        }))
        set_auth_cookie(response, token)
        return response, 201

    except IntegrityError:
        session.rollback()
        return jsonify({"error": "Email already registered / database integrity error"}), 409
    except Exception as e:
        session.rollback()
        return jsonify({"error": f"Registration failed: {str(e)}"}), 500
    finally:
        session.close()


@auth_bp.route("/login", methods=["POST"])
def login():
    """Authenticate user and return JWT in cookie."""
    data = request.get_json()

    email = data.get("email", "").lower().strip()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    session = db_session()
    try:
        user = session.query(User).filter_by(email=email).first()

        if not user or not verify_password(password, user.password_hash):
            return jsonify({"error": "Invalid email or password"}), 401

        token = create_token(user.id, user.company_id, user.role)
        company = session.query(Company).get(user.company_id)

        response = make_response(jsonify({
            "message": "Login successful",
            "user": user.to_dict(),
            "company": company.to_dict() if company else None,
        }))
        set_auth_cookie(response, token)
        return response

    finally:
        session.close()


@auth_bp.route("/logout", methods=["POST"])
def logout():
    """Clear auth cookie."""
    response = make_response(jsonify({"message": "Logged out"}))
    clear_auth_cookie(response)
    return response


@auth_bp.route("/me", methods=["GET"])
@login_required
def get_current_user():
    """Return current authenticated user info."""
    session = db_session()
    try:
        user = session.query(User).get(g.user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404

        company = session.query(Company).get(g.company_id)

        return jsonify({
            "user": user.to_dict(),
            "company": company.to_dict() if company else None,
        })
    finally:
        session.close()


@auth_bp.route("/accept-invite/<token>", methods=["GET"])
def get_invite_info(token):
    """Get invite info for the acceptance page."""
    session = db_session()
    try:
        user = session.query(User).filter_by(invite_token=token).first()

        if not user:
            return jsonify({"error": "Invalid invite link"}), 404

        if user.invite_status == "active":
            return jsonify({"error": "Invite already accepted"}), 400

        if user.invite_expires_at and user.invite_expires_at < datetime.now(timezone.utc):
            return jsonify({"error": "Invite has expired. Ask your admin to resend."}), 410

        company = session.query(Company).get(user.company_id)

        return jsonify({
            "name": user.name,
            "email": user.email,
            "company_name": company.name if company else "",
        })
    finally:
        session.close()


@auth_bp.route("/accept-invite/<token>", methods=["POST"])
def accept_invite(token):
    """Accept invite and set password."""
    data = request.get_json()
    password = data.get("password", "")

    if len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters"}), 400

    session = db_session()
    try:
        user = session.query(User).filter_by(invite_token=token).first()

        if not user:
            return jsonify({"error": "Invalid invite link"}), 404

        if user.invite_status == "active":
            return jsonify({"error": "Invite already accepted"}), 400

        if user.invite_expires_at and user.invite_expires_at < datetime.now(timezone.utc):
            return jsonify({"error": "Invite has expired. Ask your admin to resend."}), 410

        # Activate user
        user.password_hash = hash_password(password)
        user.invite_status = "active"
        user.invite_token = None
        user.invite_expires_at = None
        session.commit()

        # Log them in
        auth_token = create_token(user.id, user.company_id, user.role)
        response = make_response(jsonify({
            "message": "Account activated successfully",
            "user": user.to_dict(),
        }))
        set_auth_cookie(response, auth_token)
        return response

    except Exception as e:
        session.rollback()
        return jsonify({"error": f"Activation failed: {str(e)}"}), 500
    finally:
        session.close()
