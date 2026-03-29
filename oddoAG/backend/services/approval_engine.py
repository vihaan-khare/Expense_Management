"""Approval Engine — The core state machine for expense approval workflow."""

from datetime import datetime, timezone
from backend.database import db_session
from backend.models import (
    Expense, ApprovalChain, ChainStep, ConditionalRule,
    ApprovalAction, ExpenseComment, Notification, User
)


class ApprovalEngine:
    """
    Manages the approval state machine.
    
    Two systems run simultaneously:
    1. Sequential Chain — ordered list of approval steps
    2. Conditional Rules — auto-approve based on percentage or key approver
    
    Modes:
    - sequential: pure sequential chain, no conditional rules
    - conditional: conditional rules only, no sequential chain
    - hybrid: both systems, conditional can short-circuit the chain
    """

    @staticmethod
    def submit_expense(session, expense, employee):
        """
        Initialize the approval flow when an expense is submitted.
        Routes based on amount threshold rules:
        < Threshold -> Manager
        > Threshold -> Admin
        """
        company_id = expense.company_id

        # Get active approval chain
        chain = session.query(ApprovalChain).filter_by(
            company_id=company_id, is_active=True
        ).first()

        amount = expense.converted_amount or expense.amount
        requires_admin = False

        if chain:
            rule = session.query(ConditionalRule).filter_by(
                chain_id=chain.id, rule_type="amount"
            ).first()
            
            if rule and rule.amount_threshold and amount > rule.amount_threshold:
                requires_admin = True

        expense.total_steps = 1
        expense.current_step = 1

        if requires_admin:
            expense.status = "in_review"
            _create_comment(session, expense.id, employee.id, "submission",
                            expense.description + "\n\n(Routed to Admin - Exceeds Threshold)")
            
            admins = session.query(User).filter(
                User.company_id == company_id,
                User.role == "admin"
            ).all()
            for admin in admins:
                _create_notification(
                    session, admin.id, expense.id,
                    "approval_required",
                    f"High-value expense from {employee.name} requires Admin approval (${amount:.2f})"
                )
        else:
            # Route to Manager. Wait, if they have a direct manager, route there. Else any manager.
            has_manager_prestep = (
                employee.is_manager_approver and
                employee.direct_manager_id is not None
            )

            if has_manager_prestep:
                expense.status = "pending_manager"
                expense.current_step = 0
                _create_notification(
                    session, employee.direct_manager_id, expense.id,
                    "approval_required",
                    f"New expense from {employee.name} requires your approval (${amount:.2f})"
                )
            else:
                expense.status = "in_review"
                managers = session.query(User).filter(
                    User.company_id == company_id,
                    User.role.in_(["manager", "admin"])
                ).all()
                for manager in managers:
                    _create_notification(
                        session, manager.id, expense.id,
                        "approval_required",
                        f"Expense from {employee.name} requires Manager approval (${amount:.2f})"
                    )
            
            _create_comment(session, expense.id, employee.id, "submission", expense.description)
            
        session.flush()

    @staticmethod
    def process_action(session, expense, approver, action, justification,
                       change_reasons=None):
        """
        Process an approval action. This is the core state machine.
        """
        chain = session.query(ApprovalChain).filter_by(
            company_id=expense.company_id, is_active=True
        ).first()

        current_step = expense.current_step

        # Record the approval action
        approval_action = ApprovalAction(
            expense_id=expense.id,
            approver_id=approver.id,
            step_number=current_step,
            action=action,
            justification=justification,
            change_reasons=change_reasons,
        )
        session.add(approval_action)

        # Create thread entry
        comment_type_map = {
            "approved": "approval",
            "changes_requested": "changes_requested",
            "rejected": "rejection",
        }
        comment_content = justification
        if change_reasons:
            comment_content += "\n\nReasons: " + ", ".join(change_reasons)

        _create_comment(session, expense.id, approver.id,
                        comment_type_map[action], comment_content)

        # Get employee for notifications
        employee = session.query(User).get(expense.employee_id)



        # ─── Handle APPROVAL ─────────────────────────────────────────
        if not chain:
            # Fallback for expenses submitted before a chain was created
            expense.status = "approved"
            _create_notification(
                session, expense.employee_id, expense.id, "approved",
                f"Your expense was approved by {approver.name} (Default Routing)"
            )
            session.flush()
            return {
                "status": "approved",
                "message": f"Approved (Default Routing)",
                "auto_approved": False,
            }

        # ─── Handle REJECTION ─────────────────────────────────────────
        if action == "rejected":
            expense.status = "rejected"
            _create_notification(
                session, expense.employee_id, expense.id, "rejected",
                f"Your expense was rejected by {approver.name}: {justification[:100]}"
            )
            session.flush()
            return {"status": "rejected", "message": "Expense rejected"}

        # ─── Handle CHANGES REQUESTED ─────────────────────────────────
        if action == "changes_requested":
            expense.status = "changes_requested"
            expense.revision_count += 1

            _create_notification(
                session, expense.employee_id, expense.id, "changes_requested",
                f"{approver.name} requested changes on your expense: {justification[:100]}"
            )
            session.flush()
            return {
                "status": "changes_requested",
                "message": "Changes requested",
                "revision_count": expense.revision_count,
                "max_revisions": expense.max_revisions,
            }

        # ─── Handle APPROVAL ─────────────────────────────────────────
        # First, check conditional rules (only in 'conditional' or 'hybrid' mode)
        if chain.mode in ("conditional", "hybrid"):
            auto_result = _evaluate_conditional_rules(
                session, chain, expense, approver
            )
            if auto_result:
                expense.status = "approved"
                expense.auto_approved = True
                expense.auto_approve_reason = auto_result

                _create_notification(
                    session, expense.employee_id, expense.id, "approved",
                    f"Your expense was auto-approved: {auto_result}"
                )
                session.flush()
                return {
                    "status": "approved",
                    "message": f"Auto-approved: {auto_result}",
                    "auto_approved": True,
                }

        # If in 'conditional' mode only (no sequential chain), and no rule triggered
        if chain.mode == "conditional":
            # In pure conditional mode, a single approval without rule trigger
            # means we need more approvals — keep in review
            expense.current_step += 1
            _create_notification(
                session, expense.employee_id, expense.id, "approved",
                f"Step {current_step} approved by {approver.name}. Awaiting further review."
            )
            session.flush()
            return {"status": "in_review", "message": "Approved at this step, awaiting rules"}

        # Sequential / Hybrid — advance to next step
        steps = session.query(ChainStep).filter_by(
            chain_id=chain.id
        ).order_by(ChainStep.step_number).all()

        if current_step == 0:
            # Manager pre-step approved — move to step 1
            if steps:
                expense.current_step = 1
                expense.status = "in_review"
                _notify_step_approver(session, steps[0], expense, employee)
            else:
                # No chain steps — approve
                expense.status = "approved"
                _create_notification(
                    session, expense.employee_id, expense.id, "approved",
                    f"Your expense was approved by {approver.name}"
                )
        else:
            # Check if this was the last step
            next_step_number = current_step + 1
            next_step = None
            for s in steps:
                if s.step_number == next_step_number:
                    next_step = s
                    break

            if next_step:
                # Advance to next step
                expense.current_step = next_step_number
                expense.status = "in_review"
                _notify_step_approver(session, next_step, expense, employee)
            else:
                # Final step completed — approve
                expense.status = "approved"
                _create_notification(
                    session, expense.employee_id, expense.id, "approved",
                    f"Your expense has been fully approved!"
                )

        session.flush()
        return {
            "status": expense.status,
            "message": f"Step {current_step} approved",
            "current_step": expense.current_step,
        }

    @staticmethod
    def resubmit_expense(session, expense, employee):
        """Handle resubmission after changes were requested."""
        # Find which step requested changes
        last_action = session.query(ApprovalAction).filter_by(
            expense_id=expense.id,
            action="changes_requested"
        ).order_by(ApprovalAction.created_at.desc()).first()

        if last_action:
            expense.current_step = last_action.step_number
            if last_action.step_number == 0:
                expense.status = "pending_manager"
                # Re-notify manager
                _create_notification(
                    session, employee.direct_manager_id, expense.id,
                    "revision_submitted",
                    f"{employee.name} has resubmitted expense for review"
                )
            else:
                expense.status = "in_review"
                # Re-notify the step approver
                chain = session.query(ApprovalChain).filter_by(
                    company_id=expense.company_id, is_active=True
                ).first()
                if chain:
                    step = session.query(ChainStep).filter_by(
                        chain_id=chain.id, step_number=last_action.step_number
                    ).first()
                    if step:
                        _notify_step_approver(session, step, expense, employee)

        _create_comment(session, expense.id, employee.id, "revision_submitted",
                        "Expense resubmitted for review")
        session.flush()


def _evaluate_conditional_rules(session, chain, expense, current_approver):
    """
    Evaluate conditional rules after an approval.
    Returns auto-approve reason string if triggered, else None.
    """
    rules = session.query(ConditionalRule).filter_by(chain_id=chain.id).all()

    if not rules:
        return None

    for rule in rules:
        # Count approved actions for this expense
        approved_count = session.query(ApprovalAction).filter_by(
            expense_id=expense.id, action="approved"
        ).count()

        total_steps = expense.total_steps
        if total_steps == 0:
            total_steps = 1  # Avoid division by zero

        if rule.rule_type in ("percentage", "hybrid"):
            if rule.percentage_threshold:
                percentage = (approved_count / total_steps) * 100
                if percentage >= rule.percentage_threshold:
                    return (
                        f"Percentage threshold ({rule.percentage_threshold}%) met "
                        f"— {approved_count}/{total_steps} approvers"
                    )

        if rule.rule_type in ("specific", "hybrid"):
            if rule.key_approver_id and rule.key_approver_id == current_approver.id:
                key_approver_name = current_approver.name
                return f"Key approver ({key_approver_name}) approved"

    return None


def _notify_step_approver(session, step, expense, employee):
    """Create notification for the next approver in the chain."""
    if step.assigned_user_id:
        # Specific user assigned
        _create_notification(
            session, step.assigned_user_id, expense.id,
            "approval_required",
            f"Expense from {employee.name} requires your approval as {step.role_label} "
            f"(${expense.converted_amount or expense.amount:.2f})"
        )
    else:
        # Any manager can fulfil — notify all active managers in the company
        managers = session.query(User).filter(
            User.company_id == expense.company_id,
            User.role.in_(["manager", "admin"]),
            User.invite_status == "active",
        ).all()

        for manager in managers:
            _create_notification(
                session, manager.id, expense.id,
                "approval_required",
                f"Expense from {employee.name} requires {step.role_label} approval "
                f"(${expense.converted_amount or expense.amount:.2f})"
            )


def _create_comment(session, expense_id, user_id, comment_type, content):
    """Create a discussion thread entry."""
    comment = ExpenseComment(
        expense_id=expense_id,
        user_id=user_id,
        comment_type=comment_type,
        content=content,
    )
    session.add(comment)


def _create_notification(session, user_id, expense_id, notif_type, message):
    """Create an in-app notification."""
    notification = Notification(
        user_id=user_id,
        expense_id=expense_id,
        type=notif_type,
        message=message,
    )
    session.add(notification)
