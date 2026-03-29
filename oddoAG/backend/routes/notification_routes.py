"""Notification routes."""

from flask import Blueprint, jsonify, g
from backend.database import db_session
from backend.models import Notification
from backend.auth import login_required

notification_bp = Blueprint("notifications", __name__, url_prefix="/api/notifications")


@notification_bp.route("", methods=["GET"])
@login_required
def get_notifications():
    """Get user's notifications, newest first."""
    session = db_session()
    try:
        notifications = session.query(Notification).filter_by(
            user_id=g.user_id
        ).order_by(Notification.created_at.desc()).limit(50).all()

        unread_count = session.query(Notification).filter_by(
            user_id=g.user_id, is_read=False
        ).count()

        return jsonify({
            "notifications": [n.to_dict() for n in notifications],
            "unread_count": unread_count,
        })
    finally:
        session.close()


@notification_bp.route("/mark-read", methods=["POST"])
@login_required
def mark_all_read():
    """Mark all notifications as read."""
    session = db_session()
    try:
        session.query(Notification).filter_by(
            user_id=g.user_id, is_read=False
        ).update({"is_read": True})
        session.commit()

        return jsonify({"message": "All notifications marked as read"})
    except Exception as e:
        session.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        session.close()


@notification_bp.route("/unread-count", methods=["GET"])
@login_required
def unread_count():
    """Get just the unread notification count (for polling)."""
    session = db_session()
    try:
        count = session.query(Notification).filter_by(
            user_id=g.user_id, is_read=False
        ).count()
        return jsonify({"unread_count": count})
    finally:
        session.close()
