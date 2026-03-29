import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Application configuration loaded from environment variables."""

    # Flask
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"

    # Database
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///data/expenseflow.db")

    # JWT
    JWT_SECRET = os.getenv("JWT_SECRET", "dev-jwt-secret-change-in-production")
    JWT_EXPIRY_HOURS = int(os.getenv("JWT_EXPIRY_HOURS", "24"))

    # Email — Supabase (sends real invite emails)
    SUPABASE_URL = os.getenv("SUPABASE_URL", "")
    SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")

    # App URL
    APP_URL = os.getenv("APP_URL", "http://localhost:5000")

    # Tesseract OCR
    TESSERACT_CMD = os.getenv(
        "TESSERACT_CMD", r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    )

    # Upload
    MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", "5"))
    MAX_CONTENT_LENGTH = MAX_UPLOAD_SIZE_MB * 1024 * 1024
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "uploads")
    ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "pdf"}

    # Categories
    EXPENSE_CATEGORIES = [
        "Travel",
        "Meals",
        "Accommodation",
        "Equipment",
        "Software",
        "Training",
        "Marketing",
        "Other",
    ]

    # Change request reasons
    CHANGE_REQUEST_REASONS = [
        "Receipt unclear/missing",
        "Amount justification needed",
        "Wrong category selected",
        "Policy violation",
        "Requires additional information",
        "Other",
    ]
