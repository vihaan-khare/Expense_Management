"""User management routes — CRUD for admin."""

from datetime import datetime, timedelta, timezone
from flask import Blueprint, request, jsonify, g, current_app
from backend.database import db_session
from backend.models import User, Company
from backend.auth import login_required, role_required, generate_invite_token, hash_password
from backend.services.email_service import send_invite_email

user_bp = Blueprint("users", __name__, url_prefix="/api/users")


@user_bp.route("", methods=["GET"])
@login_required
@role_required("admin")
def list_users():
    """List all users in the company."""
    session = db_session()
    try:
        users = session.query(User).filter_by(company_id=g.company_id).all()
        return jsonify({
            "users": [u.to_dict(include_sensitive=True) for u in users]
        })
    finally:
        session.close()


@user_bp.route("", methods=["POST"])
@login_required
@role_required("admin")
def create_user():
    """Create a new user and generate a temporary password."""
    import string
    import random
    data = request.get_json()

    required = ["name", "email", "role"]
    for field in required:
        if not data.get(field, "").strip():
            return jsonify({"error": f"{field} is required"}), 400

    role = data["role"].lower().strip()
    if role not in ("employee", "manager"):
        return jsonify({"error": "Role must be 'employee' or 'manager'"}), 400

    session = db_session()
    try:
        # Check if email exists
        existing = session.query(User).filter_by(email=data["email"].lower().strip()).first()
        if existing:
            return jsonify({"error": "Email already registered"}), 409

        # Validate direct_manager_id if provided
        manager_id = data.get("direct_manager_id")
        if manager_id:
            manager = session.query(User).filter_by(
                id=manager_id, company_id=g.company_id
            ).first()
            if not manager:
                return jsonify({"error": "Selected manager not found"}), 404

        # Generate temp password
        temp_pwd = "P" + ''.join(random.choices(string.ascii_letters + string.digits, k=7))

        user = User(
            company_id=g.company_id,
            name=data["name"].strip(),
            email=data["email"].lower().strip(),
            password_hash=hash_password(temp_pwd),
            role=role,
            direct_manager_id=manager_id,
            is_manager_approver=bool(data.get("is_manager_approver", False)),
            invite_status="active",
        )
        session.add(user)
        session.commit()

        return jsonify({
            "message": "User created",
            "user": user.to_dict(include_sensitive=False),
            "temp_password": temp_pwd,
        }), 201

    except Exception as e:
        session.rollback()
        return jsonify({"error": f"Failed to create user: {str(e)}"}), 500
    finally:
        session.close()


@user_bp.route("/<user_id>", methods=["PUT"])
@login_required
@role_required("admin")
def update_user(user_id):
    """Update user role, manager assignment, etc."""
    data = request.get_json()

    session = db_session()
    try:
        user = session.query(User).filter_by(
            id=user_id, company_id=g.company_id
        ).first()

        if not user:
            return jsonify({"error": "User not found"}), 404

        # Don't allow changing own role
        if user_id == g.user_id and "role" in data:
            return jsonify({"error": "Cannot change your own role"}), 400

        if "role" in data:
            role = data["role"].lower().strip()
            if role not in ("admin", "manager", "employee"):
                return jsonify({"error": "Invalid role"}), 400
            user.role = role

        if "direct_manager_id" in data:
            if data["direct_manager_id"]:
                manager = session.query(User).filter_by(
                    id=data["direct_manager_id"], company_id=g.company_id
                ).first()
                if not manager:
                    return jsonify({"error": "Manager not found"}), 404
            user.direct_manager_id = data["direct_manager_id"] or None

        if "is_manager_approver" in data:
            user.is_manager_approver = bool(data["is_manager_approver"])

        if "name" in data and data["name"].strip():
            user.name = data["name"].strip()

        session.commit()
        return jsonify({
            "message": "User updated",
            "user": user.to_dict(),
        })

    except Exception as e:
        session.rollback()
        return jsonify({"error": f"Update failed: {str(e)}"}), 500
    finally:
        session.close()


@user_bp.route("/<user_id>/reset-password", methods=["POST"])
@login_required
@role_required("admin")
def reset_password(user_id):
    """Admin resetting user password."""
    import string
    import random
    from backend.auth import hash_password
    
    session = db_session()
    try:
        user = session.query(User).filter_by(
            id=user_id, company_id=g.company_id
        ).first()

        if not user:
            return jsonify({"error": "User not found"}), 404

        # Generate new random password
        temp_password = "P" + ''.join(random.choices(string.ascii_letters + string.digits, k=7))
        user.password_hash = hash_password(temp_password)
        session.commit()

        return jsonify({
            "message": "Password reset successfully",
            "temp_password": temp_password,
        })

    except Exception as e:
        session.rollback()
        return jsonify({"error": f"Reset failed: {str(e)}"}), 500
    finally:
        session.close()


@user_bp.route("/managers", methods=["GET"])
@login_required
def list_managers():
    """List all managers/admins in the company (for dropdowns)."""
    session = db_session()
    try:
        managers = session.query(User).filter(
            User.company_id == g.company_id,
            User.role.in_(["manager", "admin"]),
            User.invite_status == "active",
        ).all()
        return jsonify({
            "managers": [{"id": m.id, "name": m.name, "role": m.role} for m in managers]
        })
    finally:
        session.close()
