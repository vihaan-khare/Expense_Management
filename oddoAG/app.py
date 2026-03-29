"""ExpenseFlow — Flask app entry point."""

import os
from flask import Flask, send_from_directory
from flask_cors import CORS
from config import Config
from backend.database import init_db, db_session
from backend.services.email_service import init_mail


def create_app():
    """Create and configure the Flask application."""
    app = Flask(
        __name__,
        static_folder="frontend",
        static_url_path="",
    )

    app.config.from_object(Config)
    app.config["MAX_CONTENT_LENGTH"] = Config.MAX_CONTENT_LENGTH
    app.config["APP_URL"] = Config.APP_URL

    # CORS
    CORS(app, supports_credentials=True)

    # Email
    try:
        init_mail(app)
    except Exception as e:
        print(f"⚠ Email not configured: {e}")

    # Ensure upload directory exists
    upload_dir = os.path.join(os.path.dirname(__file__), Config.UPLOAD_FOLDER)
    os.makedirs(upload_dir, exist_ok=True)

    # Register blueprints
    from backend.routes.auth_routes import auth_bp
    from backend.routes.user_routes import user_bp
    from backend.routes.expense_routes import expense_bp
    from backend.routes.approval_routes import approval_bp
    from backend.routes.comment_routes import comment_bp
    from backend.routes.appeal_routes import appeal_bp
    from backend.routes.notification_routes import notification_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(expense_bp)
    app.register_blueprint(approval_bp)
    app.register_blueprint(comment_bp)
    app.register_blueprint(appeal_bp)
    app.register_blueprint(notification_bp)

    # ─── Serve frontend ──────────────────────────────────────────────
    @app.route("/")
    def serve_index():
        return send_from_directory("frontend", "index.html")

    @app.route("/uploads/<path:filename>")
    def serve_upload(filename):
        return send_from_directory(Config.UPLOAD_FOLDER, filename)

    # Catch-all for SPA routing
    @app.errorhandler(404)
    def not_found(e):
        # If it's an API route, return JSON error
        from flask import request
        if request.path.startswith("/api/"):
            return {"error": "Not found"}, 404
        # Otherwise serve the SPA
        return send_from_directory("frontend", "index.html")

    # Clean up DB sessions
    @app.teardown_appcontext
    def shutdown_session(exception=None):
        db_session.remove()

    # Initialize database
    with app.app_context():
        init_db()

    return app


if __name__ == "__main__":
    app = create_app()
    print("\n" + "=" * 50)
    print("  ExpenseFlow is running!")
    print(f"  → http://localhost:5000")
    print("=" * 50 + "\n")
    app.run(host="0.0.0.0", port=5000, debug=Config.DEBUG)
