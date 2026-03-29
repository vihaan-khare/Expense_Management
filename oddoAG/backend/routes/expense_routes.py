"""Expense routes — CRUD, submission, OCR, file upload."""

import os
from datetime import datetime, date
from flask import Blueprint, request, jsonify, g, current_app
from werkzeug.utils import secure_filename
from backend.database import db_session
from backend.models import Expense, User, Company, ApprovalAction
from backend.auth import login_required, role_required
from backend.services.currency_service import convert_currency, get_all_currencies, get_exchange_rates
from backend.services.country_service import get_countries
from backend.services.ocr_service import scan_receipt
from backend.services.approval_engine import ApprovalEngine
from config import Config

expense_bp = Blueprint("expenses", __name__, url_prefix="/api/expenses")


def _allowed_file(filename):
    return "." in filename and \
        filename.rsplit(".", 1)[1].lower() in Config.ALLOWED_EXTENSIONS


@expense_bp.route("", methods=["POST"])
@login_required
def create_expense():
    """Create and submit a new expense."""
    data = request.get_json()

    # Validate required fields
    required = ["amount", "currency", "category", "description", "expense_date"]
    for field in required:
        if not data.get(field):
            return jsonify({"error": f"{field} is required"}), 400

    try:
        amount = float(data["amount"])
        if amount <= 0:
            raise ValueError
    except (ValueError, TypeError):
        return jsonify({"error": "Amount must be a positive number"}), 400

    if len(data.get("description", "")) < 10:
        return jsonify({"error": "Description must be at least 10 characters"}), 400

    try:
        expense_date = datetime.strptime(data["expense_date"], "%Y-%m-%d").date()
        if expense_date > date.today():
            return jsonify({"error": "Expense date cannot be in the future"}), 400
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400

    if data["category"] not in Config.EXPENSE_CATEGORIES:
        return jsonify({"error": f"Invalid category. Must be one of: {', '.join(Config.EXPENSE_CATEGORIES)}"}), 400

    session = db_session()
    try:
        employee = session.query(User).get(g.user_id)
        company = session.query(Company).get(g.company_id)

        if not employee or not company:
            return jsonify({"error": "User or company not found"}), 404

        # Currency conversion
        converted_amount = amount
        if data["currency"].upper() != company.currency_code.upper():
            converted = convert_currency(amount, data["currency"], company.currency_code)
            if converted is not None:
                converted_amount = converted
            else:
                return jsonify({"error": "Currency conversion failed. Please try again."}), 500

        expense = Expense(
            company_id=g.company_id,
            employee_id=g.user_id,
            amount=amount,
            currency=data["currency"].upper(),
            converted_amount=converted_amount,
            category=data["category"],
            description=data["description"],
            expense_date=expense_date,
            receipt_url=data.get("receipt_url"),
            ocr_autofilled=data.get("ocr_autofilled", False),
        )
        session.add(expense)
        session.flush()

        # Submit through approval engine
        ApprovalEngine.submit_expense(session, expense, employee)
        session.commit()

        return jsonify({
            "message": "Expense submitted successfully",
            "expense": expense.to_dict(include_employee=True),
        }), 201

    except Exception as e:
        session.rollback()
        return jsonify({"error": f"Failed to create expense: {str(e)}"}), 500
    finally:
        session.close()


@expense_bp.route("", methods=["GET"])
@login_required
def list_expenses():
    """List expenses filtered by role."""
    session = db_session()
    try:
        if g.role == "admin":
            # Admin sees all company expenses
            expenses = session.query(Expense).filter_by(
                company_id=g.company_id
            ).order_by(Expense.created_at.desc()).all()
        elif g.role == "employee":
            # Employee sees only their own
            expenses = session.query(Expense).filter_by(
                employee_id=g.user_id
            ).order_by(Expense.created_at.desc()).all()
        else:
            # Manager — see own + direct reports
            expenses = session.query(Expense).filter_by(
                employee_id=g.user_id
            ).order_by(Expense.created_at.desc()).all()

            # Also include direct reports' expenses
            reports = session.query(User).filter_by(
                direct_manager_id=g.user_id
            ).all()
            report_ids = [r.id for r in reports]
            if report_ids:
                report_expenses = session.query(Expense).filter(
                    Expense.employee_id.in_(report_ids)
                ).order_by(Expense.created_at.desc()).all()
                expenses = list(expenses) + report_expenses

        return jsonify({
            "expenses": [e.to_dict(include_employee=True) for e in expenses]
        })
    finally:
        session.close()


@expense_bp.route("/<expense_id>", methods=["GET"])
@login_required
def get_expense(expense_id):
    """Get full expense detail with approval actions."""
    session = db_session()
    try:
        expense = session.query(Expense).get(expense_id)
        if not expense:
            return jsonify({"error": "Expense not found"}), 404

        # Access control
        if g.role == "employee" and expense.employee_id != g.user_id:
            return jsonify({"error": "Access denied"}), 403

        if g.role == "manager" and expense.company_id != g.company_id:
            return jsonify({"error": "Access denied"}), 403

        data = expense.to_dict(include_employee=True)

        # Include approval actions
        actions = session.query(ApprovalAction).filter_by(
            expense_id=expense_id
        ).order_by(ApprovalAction.created_at).all()
        data["approval_actions"] = [a.to_dict() for a in actions]

        # Include chain steps info
        from backend.models import ApprovalChain, ChainStep
        chain = session.query(ApprovalChain).filter_by(
            company_id=expense.company_id, is_active=True
        ).first()
        if chain:
            steps = session.query(ChainStep).filter_by(
                chain_id=chain.id
            ).order_by(ChainStep.step_number).all()
            data["chain_steps"] = [s.to_dict() for s in steps]
            data["chain_mode"] = chain.mode
        else:
            data["chain_steps"] = []
            data["chain_mode"] = None

        # Check if current user can act on this expense
        data["can_approve"] = _can_user_approve(session, expense, g.user_id, g.role)

        # Get employee info
        employee = session.query(User).get(expense.employee_id)
        if employee:
            data["employee_name"] = employee.name
            data["employee_email"] = employee.email
            data["has_manager_prestep"] = (
                employee.is_manager_approver and
                employee.direct_manager_id is not None
            )

        return jsonify({"expense": data})
    finally:
        session.close()


@expense_bp.route("/<expense_id>/resubmit", methods=["POST"])
@login_required
def resubmit_expense(expense_id):
    """Resubmit expense after changes were requested."""
    session = db_session()
    try:
        expense = session.query(Expense).get(expense_id)
        if not expense:
            return jsonify({"error": "Expense not found"}), 404

        if expense.employee_id != g.user_id:
            return jsonify({"error": "Only the submitter can resubmit"}), 403

        if expense.status != "changes_requested":
            return jsonify({"error": "Expense is not in 'changes requested' status"}), 400

        if expense.revision_count >= expense.max_revisions:
            return jsonify({"error": "Maximum revisions reached"}), 400

        # Update expense fields if provided
        data = request.get_json() or {}
        if data.get("amount"):
            expense.amount = float(data["amount"])
            company = session.query(Company).get(g.company_id)
            if company and expense.currency != company.currency_code:
                converted = convert_currency(expense.amount, expense.currency, company.currency_code)
                if converted:
                    expense.converted_amount = converted
        if data.get("description"):
            expense.description = data["description"]
        if data.get("category"):
            expense.category = data["category"]

        employee = session.query(User).get(g.user_id)
        ApprovalEngine.resubmit_expense(session, expense, employee)
        session.commit()

        return jsonify({
            "message": "Expense resubmitted for review",
            "expense": expense.to_dict(),
        })
    except Exception as e:
        session.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        session.close()


@expense_bp.route("/<expense_id>", methods=["DELETE"])
@login_required
def delete_expense(expense_id):
    """Delete an expense (only if pending or rejected)."""
    session = db_session()
    try:
        expense = session.query(Expense).get(expense_id)
        if not expense:
            return jsonify({"error": "Expense not found"}), 404

        if g.role != "admin" and expense.employee_id != g.user_id:
            return jsonify({"error": "Access denied"}), 403

        if expense.status not in ("pending_manager", "in_review", "changes_requested", "rejected") and g.role != "admin":
            return jsonify({"error": "Cannot delete an approved expense"}), 400

        # Delete related actions, comments, notifications first
        from backend.models import ApprovalAction, ExpenseComment, Notification
        session.query(ApprovalAction).filter_by(expense_id=expense_id).delete()
        session.query(ExpenseComment).filter_by(expense_id=expense_id).delete()
        session.query(Notification).filter_by(expense_id=expense_id).delete()
        
        session.delete(expense)
        session.commit()
        return jsonify({"message": "Expense deleted successfully"})
    except Exception as e:
        session.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        session.close()


@expense_bp.route("/upload-receipt", methods=["POST"])
@login_required
def upload_receipt():
    """Upload a receipt file."""
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    if not _allowed_file(file.filename):
        return jsonify({"error": "File type not allowed. Use jpg, png, or pdf."}), 400

    filename = secure_filename(f"{g.user_id}_{int(datetime.now().timestamp())}_{file.filename}")
    upload_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                              Config.UPLOAD_FOLDER)
    os.makedirs(upload_dir, exist_ok=True)

    filepath = os.path.join(upload_dir, filename)
    file.save(filepath)

    receipt_url = f"/uploads/{filename}"

    return jsonify({
        "message": "Receipt uploaded",
        "receipt_url": receipt_url,
        "filepath": filepath,
    })


@expense_bp.route("/ocr-scan", methods=["POST"])
@login_required
def ocr_scan():
    """Scan an uploaded receipt using OCR."""
    data = request.get_json()
    filepath = data.get("filepath", "")

    if not filepath or not os.path.exists(filepath):
        return jsonify({"error": "Receipt file not found. Upload first."}), 400

    result = scan_receipt(filepath)

    if result.get("error"):
        return jsonify(result), 422

    return jsonify({
        "message": "Receipt scanned successfully",
        "data": result,
    })


@expense_bp.route("/currencies", methods=["GET"])
@login_required
def list_currencies():
    """Get list of all available currencies."""
    return jsonify({"currencies": get_all_currencies()})


@expense_bp.route("/convert", methods=["GET"])
@login_required
def convert():
    """Convert currency amount."""
    amount = request.args.get("amount", type=float)
    from_curr = request.args.get("from", "")
    to_curr = request.args.get("to", "")

    if not amount or not from_curr or not to_curr:
        return jsonify({"error": "amount, from, and to are required"}), 400

    result = convert_currency(amount, from_curr, to_curr)
    if result is None:
        return jsonify({"error": "Conversion failed"}), 500

    return jsonify({
        "amount": amount,
        "from": from_curr.upper(),
        "to": to_curr.upper(),
        "converted_amount": result,
    })


@expense_bp.route("/countries", methods=["GET"])
def list_countries():
    """Get list of all countries with currencies (public — used on signup)."""
    return jsonify({"countries": get_countries()})


@expense_bp.route("/stats", methods=["GET"])
@login_required
@role_required("admin")
def get_stats():
    """Get dashboard statistics."""
    session = db_session()
    try:
        from sqlalchemy import func
        now = datetime.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        base_query = session.query(Expense).filter_by(company_id=g.company_id)

        total_this_month = base_query.filter(
            Expense.created_at >= month_start
        ).count()

        pending = base_query.filter(
            Expense.status.in_(["pending_manager", "in_review", "submitted"])
        ).count()

        approved_this_month = base_query.filter(
            Expense.status == "approved",
            Expense.updated_at >= month_start,
        ).count()

        rejected_this_month = base_query.filter(
            Expense.status == "rejected",
            Expense.updated_at >= month_start,
        ).count()

        total_amount = base_query.filter(
            Expense.status == "approved",
            Expense.updated_at >= month_start,
        ).with_entities(func.sum(Expense.converted_amount)).scalar() or 0

        return jsonify({
            "total_this_month": total_this_month,
            "pending_approvals": pending,
            "approved_this_month": approved_this_month,
            "rejected_this_month": rejected_this_month,
            "total_approved_amount": round(total_amount, 2),
        })
    finally:
        session.close()


def _can_user_approve(session, expense, user_id, role):
    """Check if the current user can take an approval action on this expense."""
    if expense.status not in ("pending_manager", "in_review"):
        return False

    if role == "admin":
        return True

    # Check manager pre-step
    if expense.status == "pending_manager" and expense.current_step == 0:
        employee = session.query(User).get(expense.employee_id)
        if employee and employee.direct_manager_id == user_id:
            return True

    # Check if assigned to this step
    if expense.status == "in_review":
        from backend.models import ApprovalChain, ChainStep
        chain = session.query(ApprovalChain).filter_by(
            company_id=expense.company_id, is_active=True
        ).first()
        if chain:
            step = session.query(ChainStep).filter_by(
                chain_id=chain.id, step_number=expense.current_step
            ).first()
            if step:
                if step.assigned_user_id == user_id:
                    return True
                if step.assigned_user_id is None and role in ("manager", "admin"):
                    return True

    return False
