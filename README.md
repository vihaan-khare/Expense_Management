# ExpenseFlow

ExpenseFlow is a full-stack expense management system built for teams. It handles the entire lifecycle of a business expense — from an employee snapping a photo of a receipt right through to final approval or rejection — with a configurable approval chain sitting in the middle. It is built with Flask on the backend and a vanilla JavaScript single-page application on the frontend, using SQLite as the database out of the box.

---

## What it does

At its core, ExpenseFlow gives companies a structured way to handle employee expense claims. Instead of spreadsheets and email chains, every expense goes through a defined workflow with real accountability at each step.

Employees submit expenses with a receipt (image or PDF), a category, an amount, and a description. The system then routes that expense through whichever approval chain the admin has configured — whether that is a simple manager sign-off, a multi-step sequential review, or a rules-based conditional flow. Approvers can approve, request changes, or reject. If an expense is rejected, the employee can file a formal appeal, which goes to an admin for a final decision.

There is also a receipt scanning feature built in. When an employee uploads a receipt image, Tesseract OCR reads it and tries to pull out the merchant name, total amount, currency, date, and a suggested category automatically. This is optional and the app degrades gracefully if Tesseract is not installed.

---

## Project structure

```
oddoAG/
├── app.py                        # Flask app factory and entry point
├── config.py                     # All configuration, loaded from environment variables
├── requirements.txt              # Python dependencies
├── data/
│   └── expenseflow.db            # SQLite database (auto-created on first run)
├── uploads/                      # Uploaded receipt files (auto-created on first run)
├── backend/
│   ├── auth.py                   # JWT creation, verification, and route decorators
│   ├── database.py               # SQLAlchemy engine, session, and init_db()
│   ├── models.py                 # All 10 database models
│   ├── routes/
│   │   ├── auth_routes.py        # Signup, login, logout, invite acceptance
│   │   ├── user_routes.py        # User management and team listing
│   │   ├── expense_routes.py     # Expense CRUD, file upload, OCR scan, currency conversion
│   │   ├── approval_routes.py    # Approval chain config and approval actions
│   │   ├── appeal_routes.py      # Appeal submission and admin review
│   │   ├── comment_routes.py     # Discussion thread on each expense
│   │   └── notification_routes.py# Notification listing and mark-as-read
│   └── services/
│       ├── approval_engine.py    # The core state machine driving the approval workflow
│       ├── ocr_service.py        # Tesseract-based receipt scanning
│       ├── currency_service.py   # Currency conversion
│       ├── country_service.py    # Country and currency listing
│       └── email_service.py      # Email sending via Flask-Mail
└── frontend/
    ├── index.html                # Single HTML shell — all pages are rendered by JS
    ├── css/
    │   └── styles.css
    └── js/
        ├── app.js                # Router and app bootstrap
        ├── api.js                # All API calls in one place
        ├── components.js         # Shared UI components
        ├── utils.js              # Utility helpers
        └── pages/
            ├── login.js
            ├── signup.js
            ├── dashboard.js
            ├── submit-expense.js
            ├── my-expenses.js
            ├── expense-detail.js
            ├── approver-queue.js
            ├── approval-config.js
            ├── appeals.js
            ├── users.js
            └── invite.js
```

---

## Getting started

### Prerequisites

- Python 3.10 or higher
- pip
- Tesseract OCR (optional, only needed for receipt scanning)

On macOS you can install Tesseract with `brew install tesseract`. On Ubuntu/Debian, use `sudo apt install tesseract-ocr`. On Windows, download the installer from the official Tesseract at UB Mannheim releases page, and note the installation path — you will need it for the config.

### Installation

Clone the repository and set up a virtual environment:

```bash
git clone <your-repo-url>
cd Expense_Management-main/oddoAG

python -m venv venv
source venv/bin/activate        # On Windows: venv\Scripts\activate

pip install -r requirements.txt
```

### Environment variables

Create a `.env` file in the `oddoAG/` directory. All variables have fallback defaults so the app will run without a `.env` file, but you should set these properly for anything beyond local testing:

```env
# Flask
SECRET_KEY=your-secret-key-here
FLASK_DEBUG=false

# Database (defaults to SQLite in the data/ folder)
DATABASE_URL=sqlite:///data/expenseflow.db

# JWT
JWT_SECRET=your-jwt-secret-here
JWT_EXPIRY_HOURS=24

# App URL (used in invite emails)
APP_URL=http://localhost:5000

# Tesseract OCR (path to the tesseract executable)
# macOS/Linux: /usr/local/bin/tesseract or /usr/bin/tesseract
# Windows: C:\Program Files\Tesseract-OCR\tesseract.exe
TESSERACT_CMD=/usr/local/bin/tesseract

# File uploads
MAX_UPLOAD_SIZE_MB=5
UPLOAD_FOLDER=uploads

# Email (optional — only needed if you want invite emails to actually send)
# The app uses Flask-Mail. Configure your SMTP settings here.
MAIL_SERVER=smtp.example.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=your@email.com
MAIL_PASSWORD=yourpassword
```

### Running the app

```bash
python app.py
```

The app will start on `http://localhost:5000`. The database and uploads folder are created automatically on first run. You should see:

```
==================================================
  ExpenseFlow is running!
  → http://localhost:5000
==================================================
```

---

## How the approval workflow works

This is the most important part of the system, so it is worth understanding properly.

### Roles

There are three roles:

- Employee — can submit expenses, view their own expenses, resubmit after changes are requested, and file appeals on rejected expenses.
- Manager — can do everything an employee can, plus review and act on expenses in their approval queue.
- Admin — full access. Configures the approval chain, manages users, reviews appeals, and can see all expenses across the company.

### Expense statuses

An expense moves through these statuses during its life:

- `draft` — initial state before submission (currently expenses are submitted directly, so this is mostly internal)
- `pending_manager` — awaiting a pre-step manager review (if the employee has a direct manager assigned as an approver)
- `in_review` — actively moving through the approval chain steps
- `changes_requested` — an approver asked for revisions; the employee must resubmit
- `approved` — fully approved
- `rejected` — rejected by an approver
- `appealed` — employee has filed an appeal on a rejection

### Approval chain modes

An admin configures one active approval chain for the company. Chains can run in three modes:

- Sequential — expenses go through each step in order. Each step is assigned to a specific user or to any manager/admin in that role.
- Conditional — rules-based. For example, an amount threshold rule can route high-value expenses directly to an admin instead of going through the normal chain.
- Hybrid — both systems run together. Conditional rules can short-circuit the sequential chain when triggered.

### Amount thresholds

When an expense amount (converted to the company's base currency) exceeds a configured threshold, it routes straight to an admin for review rather than going through the normal manager chain. This is the most common conditional rule in practice.

### Manager pre-step

If an employee has a direct manager assigned and that manager is marked as an approver (`is_manager_approver = true`), the expense first lands on that manager's desk before entering the main approval chain. This is step 0, tracked with the `pending_manager` status.

### Revisions

An approver can request changes instead of outright approving or rejecting. The employee then edits the expense (amount, description, category) and resubmits. By default, each expense allows up to 3 revisions before it can no longer be resubmitted.

### Appeals

If an expense is rejected, the employee can submit a formal appeal with a written reason (minimum 50 characters) and optional supporting evidence. The expense status changes to `appealed` and an admin reviews it, making a final decision to approve or reject.

---

## API reference

All API routes are prefixed with `/api/`. Authentication uses an httpOnly JWT cookie set at login. All protected routes also accept a `Bearer` token in the `Authorization` header.

### Auth

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/auth/signup` | Register a new admin (creates a company) or join an existing one with a company code |
| POST | `/api/auth/login` | Log in and receive a JWT cookie |
| POST | `/api/auth/logout` | Clear the auth cookie |
| GET | `/api/auth/me` | Get the current user and their company |
| GET | `/api/auth/accept-invite/<token>` | Look up an invite link |
| POST | `/api/auth/accept-invite/<token>` | Accept an invite and set a password |

### Expenses

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/expenses` | Employee+ | Submit a new expense |
| GET | `/api/expenses` | Employee+ | List expenses (filtered by role) |
| GET | `/api/expenses/<id>` | Employee+ | Get full expense detail with approval history |
| POST | `/api/expenses/<id>/resubmit` | Employee | Resubmit after changes were requested |
| DELETE | `/api/expenses/<id>` | Employee/Admin | Delete an expense |
| POST | `/api/expenses/upload-receipt` | Employee+ | Upload a receipt file |
| POST | `/api/expenses/ocr-scan` | Employee+ | Run OCR on an uploaded receipt |
| GET | `/api/expenses/currencies` | Employee+ | List all available currencies |
| GET | `/api/expenses/convert` | Employee+ | Convert a currency amount |
| GET | `/api/expenses/countries` | Public | List countries and their currencies |
| GET | `/api/expenses/stats` | Admin | Dashboard statistics for the current month |

### Approvals

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/approvals/chains` | Employee+ | Get the company's approval chain configuration |
| POST | `/api/approvals/chains` | Admin | Create or update the approval chain |
| GET | `/api/approvals/queue` | Manager/Admin | Get expenses awaiting action |
| POST | `/api/approvals/expenses/<id>/action` | Manager/Admin | Take an action (approve, request changes, reject) |

### Appeals

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/expenses/<id>/appeal` | Employee | Submit an appeal on a rejected expense |
| GET | `/api/appeals` | Admin | List all pending appeals |
| POST | `/api/appeals/<id>/decide` | Admin | Approve or reject an appeal |

### Users

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/users` | Admin | List all users in the company |
| POST | `/api/users/invite` | Admin | Invite a new user by email |
| PUT | `/api/users/<id>` | Admin | Update a user (role, manager assignment) |
| DELETE | `/api/users/<id>` | Admin | Remove a user |

### Comments

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/expenses/<id>/comments` | Employee+ | Get the comment thread for an expense |
| POST | `/api/expenses/<id>/comments` | Employee+ | Add a comment |

### Notifications

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/notifications` | Employee+ | Get notifications for the current user |
| POST | `/api/notifications/<id>/read` | Employee+ | Mark a notification as read |
| POST | `/api/notifications/read-all` | Employee+ | Mark all notifications as read |

---

## Database

The app uses SQLite by default with WAL mode enabled for better concurrent read performance. The database is created automatically in `data/expenseflow.db` on first run.

For production, you can point `DATABASE_URL` at a PostgreSQL instance and the SQLAlchemy layer will handle the rest. The `check_same_thread=False` SQLite connect arg is only applied automatically when a SQLite URL is detected.

### Schema overview

There are 10 tables:

- `companies` — one row per organisation; stores name, country, currency, and a unique company code used for self-signup
- `users` — employees, managers, and admins; each belongs to a company; supports invite tokens for email-based onboarding
- `expenses` — the core record; tracks amount, currency, converted amount, category, receipt URL, OCR flag, status, current step, revision count, and timestamps
- `approval_chains` — one active chain per company; supports sequential, conditional, and hybrid modes
- `chain_steps` — the ordered steps within an approval chain; each step can be assigned to a specific user
- `conditional_rules` — rules attached to a chain (amount thresholds, percentage-based, key approver requirements)
- `approval_actions` — an audit log of every approve/reject/changes-requested action taken, with justification and timestamp
- `expense_comments` — discussion thread on each expense; includes visibility control (some comments are internal-only)
- `appeals` — formal appeals on rejected expenses; tracks submission, evidence, admin decision, and review timestamp
- `notifications` — in-app notifications for each user, linked to specific expenses

---

## OCR receipt scanning

When Tesseract is installed and configured, uploading a receipt image triggers OCR extraction. The service:

1. Opens the image and converts it to grayscale for better accuracy
2. Runs `pytesseract.image_to_string()` to extract raw text
3. Parses the text to find the merchant name (usually the first substantive line), the total amount (the largest number matching currency patterns), the currency (detected from symbols like $, £, €, ₹), the date, and a suggested category based on keyword matching (e.g. "uber" maps to Travel, "hotel" maps to Accommodation)

If Tesseract is not installed, the endpoint returns a clear error message rather than crashing. In development, if the Tesseract binary is missing but pytesseract is installed, the service falls back to mock data so you can still test the UI flow.

Allowed receipt file types are JPG, PNG, and PDF. Maximum file size defaults to 5MB and is configurable.

---

## User onboarding

There are two ways a user can join:

1. Self-signup with a company code — any employee or manager can sign up by entering the 6-character company code generated when an admin first creates the company.

2. Email invite — an admin can invite a user directly. This generates a unique invite token and (if email is configured) sends a link. The invited user sets their password via the accept-invite page. Invite tokens expire after 48 hours by default.

---

## Security notes

- Passwords are hashed using PBKDF2-SHA256 via Werkzeug.
- JWT tokens are stored as httpOnly cookies, which prevents JavaScript access.
- The `secure` flag on the auth cookie is set to `False` by default so the app works over plain HTTP in development. Set it to `True` in production behind HTTPS.
- The `SameSite=Lax` cookie policy is set to provide CSRF protection on cross-site requests.
- Role checks are enforced at the route level using the `@role_required` decorator, and row-level access control is applied in each route handler (employees can only see their own expenses, managers can only act on expenses in their company, etc.).
- The default `SECRET_KEY` and `JWT_SECRET` in `config.py` are development placeholders. Always set these to strong random values in production.

---

## Expense categories

The following categories are available when submitting an expense. This list is defined in `config.py` and validated server-side:

- Travel
- Meals
- Accommodation
- Equipment
- Software
- Training
- Marketing
- Other

---

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| flask | 3.1.1 | Web framework |
| flask-cors | 5.0.1 | Cross-origin request handling |
| sqlalchemy | 2.0.40 | ORM and database abstraction |
| pyjwt | 2.10.1 | JWT creation and verification |
| werkzeug | 3.1.3 | Password hashing and file utilities |
| requests | 2.32.3 | HTTP calls in currency and country services |
| flask-mail | 0.10.0 | Email sending |
| pytesseract | 0.3.13 | Tesseract OCR Python wrapper |
| Pillow | 11.1.0 | Image processing for OCR |
| python-dotenv | 1.1.0 | `.env` file loading |

---

## Contributing

The codebase is structured to make it easy to add new approval rules, notification types, or expense categories. The approval engine in `backend/services/approval_engine.py` is the most complex part of the system — if you are adding new workflow logic, that is where to start. All route blueprints are registered in `app.py` so adding a new module follows the same pattern as the existing ones.

If you want to swap SQLite for PostgreSQL, change `DATABASE_URL` in your `.env` and install `psycopg2-binary`. No code changes are required.
