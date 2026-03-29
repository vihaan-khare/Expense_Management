"""Discussion thread / comment routes."""

from flask import Blueprint, request, jsonify, g
from backend.database import db_session
from backend.models import ExpenseComment, Expense, User
from backend.auth import login_required

comment_bp = Blueprint("comments", __name__, url_prefix="/api/expenses")


@comment_bp.route("/<expense_id>/comments", methods=["GET"])
@login_required
def get_comments(expense_id):
    """Get all discussion thread entries for an expense."""
    session = db_session()
    try:
        expense = session.query(Expense).get(expense_id)
        if not expense:
            return jsonify({"error": "Expense not found"}), 404

        # Access control
        if g.role == "employee" and expense.employee_id != g.user_id:
            return jsonify({"error": "Access denied"}), 403

        if expense.company_id != g.company_id:
            return jsonify({"error": "Access denied"}), 403

        comments = session.query(ExpenseComment).filter_by(
            expense_id=expense_id
        ).order_by(ExpenseComment.created_at).all()

        # Filter visibility for employees
        if g.role == "employee":
            comments = [c for c in comments if c.is_visible_to_employee]

        return jsonify({
            "comments": [c.to_dict() for c in comments]
        })
    finally:
        session.close()


@comment_bp.route("/<expense_id>/comments", methods=["POST"])
@login_required
def add_comment(expense_id):
    """Add a query or reply to the discussion thread."""
    data = request.get_json()

    content = data.get("content", "").strip()
    if not content:
        return jsonify({"error": "Comment content is required"}), 400

    comment_type = data.get("comment_type", "query")
    if comment_type not in ("query", "reply"):
        return jsonify({"error": "Comment type must be 'query' or 'reply'"}), 400

    session = db_session()
    try:
        expense = session.query(Expense).get(expense_id)
        if not expense:
            return jsonify({"error": "Expense not found"}), 404

        # Access control
        if g.role == "employee" and expense.employee_id != g.user_id:
            return jsonify({"error": "Access denied"}), 403

        if expense.company_id != g.company_id:
            return jsonify({"error": "Access denied"}), 403

        comment = ExpenseComment(
            expense_id=expense_id,
            user_id=g.user_id,
            comment_type=comment_type,
            content=content,
            attachment_url=data.get("attachment_url"),
        )
        session.add(comment)
        session.commit()

        return jsonify({
            "message": "Comment added",
            "comment": comment.to_dict(),
        }), 201

    except Exception as e:
        session.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        session.close()
