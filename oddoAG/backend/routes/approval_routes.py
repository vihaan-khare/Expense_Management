"""Approval chain configuration and action routes."""

from flask import Blueprint, request, jsonify, g
from backend.database import db_session
from backend.models import (
    ApprovalChain, ChainStep, ConditionalRule, Expense, User, ApprovalAction
)
from backend.auth import login_required, role_required
from backend.services.approval_engine import ApprovalEngine

approval_bp = Blueprint("approvals", __name__, url_prefix="/api/approvals")


# ─── CHAIN CONFIGURATION (Admin Only) ────────────────────────────────────────

@approval_bp.route("/chains", methods=["GET"])
@login_required
def get_chains():
    """Get approval chain configuration for the company."""
    session = db_session()
    try:
        chains = session.query(ApprovalChain).filter_by(
            company_id=g.company_id
        ).all()
        return jsonify({
            "chains": [c.to_dict(include_steps=True, include_rules=True) for c in chains]
        })
    finally:
        session.close()


@approval_bp.route("/chains", methods=["POST"])
@login_required
@role_required("admin")
def create_or_update_chain():
    """Create or update the approval chain."""
    data = request.get_json()

    if not data.get("name", "").strip():
        return jsonify({"error": "Chain name is required"}), 400

    mode = data.get("mode", "sequential")
    if mode not in ("sequential", "conditional", "hybrid"):
        return jsonify({"error": "Mode must be sequential, conditional, or hybrid"}), 400

    session = db_session()
    try:
        # Deactivate existing chains
        existing = session.query(ApprovalChain).filter_by(
            company_id=g.company_id
        ).all()
        for c in existing:
            c.is_active = False

        # Create new chain
        chain = ApprovalChain(
            company_id=g.company_id,
            name=data["name"].strip(),
            mode=mode,
            is_active=True,
        )
        session.add(chain)
        session.flush()

        # Add steps
        steps_data = data.get("steps", [])
        for i, step_data in enumerate(steps_data):
            step = ChainStep(
                chain_id=chain.id,
                step_number=i + 1,
                role_label=step_data.get("role_label", f"Step {i + 1}"),
                assigned_user_id=step_data.get("assigned_user_id"),
            )
            session.add(step)

        # Add conditional rules
        rules_data = data.get("rules", [])
        for rule_data in rules_data:
            rule_type = rule_data.get("rule_type", "percentage")
            if rule_type not in ("percentage", "specific", "hybrid", "amount"):
                continue

            rule = ConditionalRule(
                chain_id=chain.id,
                rule_type=rule_type,
                percentage_threshold=rule_data.get("percentage_threshold"),
                amount_threshold=rule_data.get("amount_threshold"),
                key_approver_id=rule_data.get("key_approver_id"),
            )
            session.add(rule)

        session.commit()

        return jsonify({
            "message": "Approval chain configured",
            "chain": chain.to_dict(include_steps=True, include_rules=True),
        }), 201

    except Exception as e:
        session.rollback()
        return jsonify({"error": f"Failed to configure chain: {str(e)}"}), 500
    finally:
        session.close()


@approval_bp.route("/chains/<chain_id>", methods=["DELETE"])
@login_required
@role_required("admin")
def delete_chain(chain_id):
    """Delete an approval chain."""
    session = db_session()
    try:
        chain = session.query(ApprovalChain).filter_by(
            id=chain_id, company_id=g.company_id
        ).first()
        if not chain:
            return jsonify({"error": "Chain not found"}), 404

        session.delete(chain)
        session.commit()
        return jsonify({"message": "Chain deleted"})
    except Exception as e:
        session.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        session.close()


# ─── APPROVAL ACTIONS ────────────────────────────────────────────────────────

@approval_bp.route("/queue", methods=["GET"])
@login_required
def get_approval_queue():
    """Get expenses waiting for current user's approval."""
    session = db_session()
    try:
        pending_expenses = []

        # Get all expenses in approval status
        expenses = session.query(Expense).filter(
            Expense.company_id == g.company_id,
            Expense.status.in_(["pending_manager", "in_review"]),
        ).order_by(Expense.created_at).all()

        for expense in expenses:
            from backend.routes.expense_routes import _can_user_approve
            if _can_user_approve(session, expense, g.user_id, g.role):
                data = expense.to_dict(include_employee=True)
                # Calculate days waiting
                if expense.updated_at:
                    from datetime import datetime, timezone
                    delta = datetime.now(timezone.utc) - expense.updated_at.replace(tzinfo=timezone.utc) if expense.updated_at.tzinfo is None else datetime.now(timezone.utc) - expense.updated_at
                    data["days_waiting"] = delta.days
                else:
                    data["days_waiting"] = 0
                pending_expenses.append(data)

        return jsonify({"queue": pending_expenses})
    finally:
        session.close()


@approval_bp.route("/<expense_id>/action", methods=["POST"])
@login_required
def take_action(expense_id):
    """Take an approval action on an expense."""
    data = request.get_json()

    action = data.get("action", "")
    justification = data.get("justification", "")
    change_reasons = data.get("change_reasons", [])

    # Validate action
    if action not in ("approved", "changes_requested", "rejected"):
        return jsonify({"error": "Action must be: approved, changes_requested, or rejected"}), 400

    # Validate justification
    if len(justification) < 20:
        return jsonify({"error": "Justification must be at least 20 characters"}), 400

    # Reject lazy justifications for approvals
    if action == "approved":
        lazy_texts = {"ok", "approved", "looks good", "fine", "good", "lgtm", "yes", "sure"}
        if justification.strip().lower() in lazy_texts:
            return jsonify({"error": "Please provide a meaningful justification, not just a single-word confirmation"}), 400

    # Validate change_reasons for changes_requested
    if action == "changes_requested" and not change_reasons:
        return jsonify({"error": "At least one reason must be selected when requesting changes"}), 400

    session = db_session()
    try:
        expense = session.query(Expense).get(expense_id)
        if not expense:
            return jsonify({"error": "Expense not found"}), 404

        if expense.company_id != g.company_id:
            return jsonify({"error": "Access denied"}), 403

        # Check if user can approve
        from backend.routes.expense_routes import _can_user_approve
        if not _can_user_approve(session, expense, g.user_id, g.role):
            return jsonify({"error": "You are not authorized to act on this expense at this step"}), 403

        # Check revision limit for changes_requested
        if action == "changes_requested" and expense.revision_count >= expense.max_revisions:
            return jsonify({
                "error": f"Maximum revisions ({expense.max_revisions}) reached. You must approve or reject."
            }), 400

        approver = session.query(User).get(g.user_id)

        result = ApprovalEngine.process_action(
            session, expense, approver, action, justification, change_reasons
        )

        if "error" in result:
            session.rollback()
            return jsonify(result), 400

        session.commit()
        return jsonify(result)

    except Exception as e:
        session.rollback()
        return jsonify({"error": f"Action failed: {str(e)}"}), 500
    finally:
        session.close()
