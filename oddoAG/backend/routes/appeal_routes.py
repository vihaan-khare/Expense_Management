"""Appeal routes — submission and admin review."""

from datetime import datetime, timezone
from flask import Blueprint, request, jsonify, g
from backend.database import db_session
from backend.models import Appeal, Expense, User, ExpenseComment, Notification
from backend.auth import login_required, role_required

appeal_bp = Blueprint("appeals", __name__, url_prefix="/api")


@appeal_bp.route("/expenses/<expense_id>/appeal", methods=["POST"])
@login_required
def submit_appeal(expense_id):
    """Submit an appeal on a rejected expense."""
    data = request.get_json()

    reason = data.get("reason", "").strip()
    if len(reason) < 50:
        return jsonify({"error": "Appeal reason must be at least 50 characters"}), 400

    session = db_session()
    try:
        expense = session.query(Expense).get(expense_id)
        if not expense:
            return jsonify({"error": "Expense not found"}), 404

        if expense.employee_id != g.user_id:
            return jsonify({"error": "Only the submitter can appeal"}), 403

        if expense.status != "rejected":
            return jsonify({"error": "Only rejected expenses can be appealed"}), 400

        # Check if already appealed
        existing = session.query(Appeal).filter_by(expense_id=expense_id).first()
        if existing:
            return jsonify({"error": "An appeal has already been submitted for this expense"}), 409

        appeal = Appeal(
            expense_id=expense_id,
            submitted_by=g.user_id,
            reason=reason,
            evidence_url=data.get("evidence_url"),
        )
        session.add(appeal)

        expense.status = "appealed"

        # Create thread entry
        comment = ExpenseComment(
            expense_id=expense_id,
            user_id=g.user_id,
            comment_type="submission",
            content=f"Appeal submitted: {reason}",
        )
        session.add(comment)

        # Notify all admins
        admins = session.query(User).filter_by(
            company_id=g.company_id, role="admin"
        ).all()
        employee = session.query(User).get(g.user_id)
        for admin in admins:
            notif = Notification(
                user_id=admin.id,
                expense_id=expense_id,
                type="appeal_submitted",
                message=f"{employee.name} has appealed a rejected expense (${expense.converted_amount or expense.amount:.2f})",
            )
            session.add(notif)

        session.commit()

        return jsonify({
            "message": "Appeal submitted successfully",
            "appeal": appeal.to_dict(),
        }), 201

    except Exception as e:
        session.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        session.close()


@appeal_bp.route("/appeals", methods=["GET"])
@login_required
@role_required("admin")
def list_appeals():
    """List all pending appeals (admin only)."""
    session = db_session()
    try:
        appeals = session.query(Appeal).join(Expense).filter(
            Expense.company_id == g.company_id,
            Appeal.admin_decision.is_(None),
        ).order_by(Appeal.created_at).all()

        result = []
        for appeal in appeals:
            data = appeal.to_dict()
            expense = session.query(Expense).get(appeal.expense_id)
            if expense:
                data["expense"] = expense.to_dict(include_employee=True)
            result.append(data)

        return jsonify({"appeals": result})
    finally:
        session.close()


@appeal_bp.route("/appeals/<appeal_id>/review", methods=["POST"])
@login_required
@role_required("admin")
def review_appeal(appeal_id):
    """Admin reviews an appeal — approve or uphold rejection."""
    data = request.get_json()

    decision = data.get("decision", "")
    justification = data.get("justification", "").strip()

    if decision not in ("approved", "rejected"):
        return jsonify({"error": "Decision must be 'approved' or 'rejected'"}), 400

    if len(justification) < 20:
        return jsonify({"error": "Justification must be at least 20 characters"}), 400

    session = db_session()
    try:
        appeal = session.query(Appeal).get(appeal_id)
        if not appeal:
            return jsonify({"error": "Appeal not found"}), 404

        expense = session.query(Expense).get(appeal.expense_id)
        if not expense or expense.company_id != g.company_id:
            return jsonify({"error": "Access denied"}), 403

        if appeal.admin_decision:
            return jsonify({"error": "Appeal already reviewed"}), 400

        # Record decision
        appeal.admin_decision = decision
        appeal.admin_justification = justification
        appeal.reviewed_by = g.user_id
        appeal.reviewed_at = datetime.now(timezone.utc)

        if decision == "approved":
            expense.status = "approved"
            comment_type = "admin_override"
            notif_message = f"Your appeal was approved by admin: {justification[:100]}"
        else:
            expense.status = "rejected"
            comment_type = "rejection"
            notif_message = f"Your appeal was denied by admin: {justification[:100]}"

        # Create thread entry
        comment = ExpenseComment(
            expense_id=expense.id,
            user_id=g.user_id,
            comment_type=comment_type,
            content=f"Admin decision on appeal: {decision.upper()} — {justification}",
        )
        session.add(comment)

        # Notify employee
        notif = Notification(
            user_id=expense.employee_id,
            expense_id=expense.id,
            type="appeal_decided",
            message=notif_message,
        )
        session.add(notif)

        session.commit()

        return jsonify({
            "message": f"Appeal {decision}",
            "appeal": appeal.to_dict(),
        })

    except Exception as e:
        session.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        session.close()
