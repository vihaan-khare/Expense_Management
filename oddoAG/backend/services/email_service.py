"""Email service — mock implementation without actual email sending."""

from config import Config


def init_mail(app):
    """Initialize mail service (no-op for mock)."""
    pass


def send_invite_email(app, recipient_email, recipient_name, company_name, invite_token):
    """
    Mock sending invite email.
    The invite link is also returned by the API so the frontend can display it.
    """
    invite_url = f"{Config.APP_URL}/#/invite/{invite_token}"
    
    print("\n" + "="*50)
    print(f"📧 MOCK EMAIL SENT")
    print(f"To: {recipient_name} <{recipient_email}>")
    print(f"Subject: You're invited to join {company_name} on ExpenseFlow")
    print("-" * 50)
    print(f"Invite Link:")
    print(f"{invite_url}")
    print("="*50 + "\n")


def send_notification_email(app, recipient_email, subject, body_html, body_text=""):
    """Mock sending notification email."""
    print("\n" + "="*50)
    print(f"📧 MOCK NOTIFICATION SENT")
    print(f"To: {recipient_email}")
    print(f"Subject: {subject}")
    print("="*50 + "\n")
