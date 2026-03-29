"""SQLAlchemy models for all 10 database tables (9 from spec + notifications)."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, Text, DateTime, Date,
    ForeignKey, Enum, JSON, Index
)
from sqlalchemy.orm import relationship
from backend.database import Base


def generate_uuid():
    return str(uuid.uuid4())


def utc_now():
    return datetime.now(timezone.utc)


# ─── Companies ───────────────────────────────────────────────────────────────

class Company(Base):
    __tablename__ = "companies"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    country = Column(String(255), nullable=False)
    currency_code = Column(String(10), nullable=False)
    company_code = Column(String(20), nullable=True, unique=True, index=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    # Relationships
    users = relationship("User", back_populates="company", lazy="dynamic")
    expenses = relationship("Expense", back_populates="company", lazy="dynamic")
    approval_chains = relationship("ApprovalChain", back_populates="company", lazy="dynamic")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "country": self.country,
            "currency_code": self.currency_code,
            "company_code": self.company_code,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ─── Users ───────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    company_id = Column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="employee")  # admin | manager | employee
    direct_manager_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    is_manager_approver = Column(Boolean, default=False, nullable=False)
    invite_status = Column(String(20), default="active", nullable=False)  # pending | active
    invite_token = Column(String(255), nullable=True, unique=True)
    invite_expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    # Relationships
    company = relationship("Company", back_populates="users")
    direct_manager = relationship("User", remote_side=[id], foreign_keys=[direct_manager_id])
    expenses = relationship("Expense", back_populates="employee", foreign_keys="Expense.employee_id", lazy="dynamic")

    __table_args__ = (
        Index("ix_users_company_role", "company_id", "role"),
        Index("ix_users_invite_token", "invite_token"),
    )

    def to_dict(self, include_sensitive=False):
        data = {
            "id": self.id,
            "company_id": self.company_id,
            "name": self.name,
            "email": self.email,
            "role": self.role,
            "direct_manager_id": self.direct_manager_id,
            "is_manager_approver": self.is_manager_approver,
            "invite_status": self.invite_status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        if include_sensitive:
            data["invite_token"] = self.invite_token
            data["invite_expires_at"] = self.invite_expires_at.isoformat() if self.invite_expires_at else None
        return data


# ─── Expenses ────────────────────────────────────────────────────────────────

class Expense(Base):
    __tablename__ = "expenses"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    company_id = Column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    employee_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    currency = Column(String(10), nullable=False)
    converted_amount = Column(Float, nullable=True)
    category = Column(String(50), nullable=False)
    description = Column(Text, nullable=False)
    expense_date = Column(Date, nullable=False)
    receipt_url = Column(String(500), nullable=True)
    ocr_autofilled = Column(Boolean, default=False, nullable=False)
    status = Column(String(30), default="draft", nullable=False)
    # Status values: draft | submitted | pending_manager | in_review |
    #                changes_requested | approved | rejected | appealed
    current_step = Column(Integer, default=0, nullable=False)
    total_steps = Column(Integer, default=0, nullable=False)
    auto_approved = Column(Boolean, default=False, nullable=False)
    auto_approve_reason = Column(String(500), nullable=True)
    revision_count = Column(Integer, default=0, nullable=False)
    max_revisions = Column(Integer, default=3, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    company = relationship("Company", back_populates="expenses")
    employee = relationship("User", back_populates="expenses", foreign_keys=[employee_id])
    approval_actions = relationship("ApprovalAction", back_populates="expense",
                                     order_by="ApprovalAction.created_at", lazy="dynamic")
    comments = relationship("ExpenseComment", back_populates="expense",
                            order_by="ExpenseComment.created_at", lazy="dynamic")
    appeals = relationship("Appeal", back_populates="expense", lazy="dynamic")

    __table_args__ = (
        Index("ix_expenses_status", "status"),
        Index("ix_expenses_company_status", "company_id", "status"),
    )

    def to_dict(self, include_employee=False):
        data = {
            "id": self.id,
            "company_id": self.company_id,
            "employee_id": self.employee_id,
            "amount": self.amount,
            "currency": self.currency,
            "converted_amount": self.converted_amount,
            "category": self.category,
            "description": self.description,
            "expense_date": self.expense_date.isoformat() if self.expense_date else None,
            "receipt_url": self.receipt_url,
            "ocr_autofilled": self.ocr_autofilled,
            "status": self.status,
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "auto_approved": self.auto_approved,
            "auto_approve_reason": self.auto_approve_reason,
            "revision_count": self.revision_count,
            "max_revisions": self.max_revisions,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_employee and self.employee:
            data["employee_name"] = self.employee.name
            data["employee_email"] = self.employee.email
        return data


# ─── Approval Chains ─────────────────────────────────────────────────────────

class ApprovalChain(Base):
    __tablename__ = "approval_chains"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    company_id = Column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    mode = Column(String(20), nullable=False, default="sequential")  # sequential | conditional | hybrid
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    # Relationships
    company = relationship("Company", back_populates="approval_chains")
    steps = relationship("ChainStep", back_populates="chain",
                         order_by="ChainStep.step_number", cascade="all, delete-orphan")
    rules = relationship("ConditionalRule", back_populates="chain",
                         cascade="all, delete-orphan")

    def to_dict(self, include_steps=False, include_rules=False):
        data = {
            "id": self.id,
            "company_id": self.company_id,
            "name": self.name,
            "mode": self.mode,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        if include_steps:
            data["steps"] = [s.to_dict() for s in self.steps]
        if include_rules:
            data["rules"] = [r.to_dict() for r in self.rules]
        return data


# ─── Chain Steps ─────────────────────────────────────────────────────────────

class ChainStep(Base):
    __tablename__ = "chain_steps"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    chain_id = Column(String(36), ForeignKey("approval_chains.id"), nullable=False, index=True)
    step_number = Column(Integer, nullable=False)
    role_label = Column(String(100), nullable=False)
    assigned_user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    # Relationships
    chain = relationship("ApprovalChain", back_populates="steps")
    assigned_user = relationship("User", foreign_keys=[assigned_user_id])

    def to_dict(self):
        data = {
            "id": self.id,
            "chain_id": self.chain_id,
            "step_number": self.step_number,
            "role_label": self.role_label,
            "assigned_user_id": self.assigned_user_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        if self.assigned_user:
            data["assigned_user_name"] = self.assigned_user.name
        return data


# ─── Conditional Rules ───────────────────────────────────────────────────────

class ConditionalRule(Base):
    __tablename__ = "conditional_rules"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    chain_id = Column(String(36), ForeignKey("approval_chains.id"), nullable=False, index=True)
    rule_type = Column(String(20), nullable=False)  # percentage | specific | hybrid | amount
    percentage_threshold = Column(Integer, nullable=True)
    amount_threshold = Column(Float, nullable=True)
    key_approver_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    # Relationships
    chain = relationship("ApprovalChain", back_populates="rules")
    key_approver = relationship("User", foreign_keys=[key_approver_id])

    def to_dict(self):
        data = {
            "id": self.id,
            "chain_id": self.chain_id,
            "rule_type": self.rule_type,
            "percentage_threshold": self.percentage_threshold,
            "amount_threshold": self.amount_threshold,
            "key_approver_id": self.key_approver_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        if self.key_approver:
            data["key_approver_name"] = self.key_approver.name
        return data


# ─── Approval Actions ────────────────────────────────────────────────────────

class ApprovalAction(Base):
    __tablename__ = "approval_actions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    expense_id = Column(String(36), ForeignKey("expenses.id"), nullable=False, index=True)
    approver_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    step_number = Column(Integer, nullable=False)
    action = Column(String(30), nullable=False)  # approved | changes_requested | rejected
    justification = Column(Text, nullable=False)
    change_reasons = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    # Relationships
    expense = relationship("Expense", back_populates="approval_actions")
    approver = relationship("User", foreign_keys=[approver_id])

    def to_dict(self):
        data = {
            "id": self.id,
            "expense_id": self.expense_id,
            "approver_id": self.approver_id,
            "step_number": self.step_number,
            "action": self.action,
            "justification": self.justification,
            "change_reasons": self.change_reasons,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        if self.approver:
            data["approver_name"] = self.approver.name
            data["approver_role"] = self.approver.role
        return data


# ─── Expense Comments (Discussion Thread) ────────────────────────────────────

class ExpenseComment(Base):
    __tablename__ = "expense_comments"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    expense_id = Column(String(36), ForeignKey("expenses.id"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    comment_type = Column(String(30), nullable=False)
    # Types: submission | approval | rejection | changes_requested | query |
    #        reply | revision_submitted | admin_override
    content = Column(Text, nullable=False)
    attachment_url = Column(String(500), nullable=True)
    is_visible_to_employee = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    # Relationships
    expense = relationship("Expense", back_populates="comments")
    user = relationship("User", foreign_keys=[user_id])

    def to_dict(self):
        data = {
            "id": self.id,
            "expense_id": self.expense_id,
            "user_id": self.user_id,
            "comment_type": self.comment_type,
            "content": self.content,
            "attachment_url": self.attachment_url,
            "is_visible_to_employee": self.is_visible_to_employee,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        if self.user:
            data["user_name"] = self.user.name
            data["user_role"] = self.user.role
        return data


# ─── Appeals ─────────────────────────────────────────────────────────────────

class Appeal(Base):
    __tablename__ = "appeals"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    expense_id = Column(String(36), ForeignKey("expenses.id"), nullable=False, index=True)
    submitted_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    reason = Column(Text, nullable=False)
    evidence_url = Column(String(500), nullable=True)
    reviewed_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    admin_decision = Column(String(20), nullable=True)  # approved | rejected
    admin_justification = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    reviewed_at = Column(DateTime, nullable=True)

    # Relationships
    expense = relationship("Expense", back_populates="appeals")
    submitter = relationship("User", foreign_keys=[submitted_by])
    reviewer = relationship("User", foreign_keys=[reviewed_by])

    def to_dict(self):
        data = {
            "id": self.id,
            "expense_id": self.expense_id,
            "submitted_by": self.submitted_by,
            "reason": self.reason,
            "evidence_url": self.evidence_url,
            "reviewed_by": self.reviewed_by,
            "admin_decision": self.admin_decision,
            "admin_justification": self.admin_justification,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
        }
        if self.submitter:
            data["submitter_name"] = self.submitter.name
        if self.reviewer:
            data["reviewer_name"] = self.reviewer.name
        return data


# ─── Notifications ───────────────────────────────────────────────────────────

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    expense_id = Column(String(36), ForeignKey("expenses.id"), nullable=True)
    type = Column(String(50), nullable=False)
    # Types: approval_required | approved | rejected | changes_requested |
    #        appeal_submitted | appeal_decided | revision_submitted
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    expense = relationship("Expense", foreign_keys=[expense_id])

    __table_args__ = (
        Index("ix_notifications_user_unread", "user_id", "is_read"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "expense_id": self.expense_id,
            "type": self.type,
            "message": self.message,
            "is_read": self.is_read,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
