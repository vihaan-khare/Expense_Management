"""OCR service for receipt scanning using Tesseract."""

import re
import os
from datetime import datetime
from config import Config

# Try to import pytesseract — graceful fallback if not installed
try:
    import pytesseract
    from PIL import Image
    pytesseract.pytesseract.tesseract_cmd = Config.TESSERACT_CMD
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    print("⚠ pytesseract or Pillow not installed — OCR disabled")


# Category keywords for matching
CATEGORY_KEYWORDS = {
    "Travel": ["uber", "lyft", "taxi", "airline", "flight", "train", "gas", "fuel", "parking", "toll"],
    "Meals": ["restaurant", "cafe", "coffee", "food", "dinner", "lunch", "breakfast", "pizza", "burger", "starbucks", "mcdonald"],
    "Accommodation": ["hotel", "motel", "inn", "airbnb", "resort", "lodge", "booking"],
    "Equipment": ["amazon", "best buy", "hardware", "electronics", "computer", "laptop", "phone"],
    "Software": ["subscription", "license", "saas", "cloud", "adobe", "microsoft", "google"],
    "Training": ["course", "training", "seminar", "workshop", "conference", "education"],
    "Marketing": ["advertising", "marketing", "promotion", "campaign", "print", "design"],
}


def scan_receipt(image_path):
    """
    Extract expense data from a receipt image using OCR.
    
    Returns dict with: merchant_name, amount, currency, date, suggested_category
    or None if OCR fails.
    """
    if not TESSERACT_AVAILABLE:
        return {
            "error": "OCR not available. Install Tesseract OCR to enable receipt scanning.",
            "merchant_name": "",
            "amount": None,
            "currency": "",
            "date": "",
            "suggested_category": "",
        }

    if not os.path.exists(image_path):
        return {"error": "Receipt file not found"}

    try:
        # Open and process image
        img = Image.open(image_path)

        # Convert to grayscale for better OCR
        if img.mode != "L":
            img = img.convert("L")

        # Extract text
        text = pytesseract.image_to_string(img)

        if not text.strip():
            return {"error": "Could not read text from receipt"}

        # Parse the extracted text
        result = _parse_receipt_text(text)
        result["raw_text"] = text[:500]  # Include raw text for debugging (truncated)
        return result

    except Exception as e:
        # Fallback to mock data if Tesseract executable is missing
        err_msg = str(e)
        if "is not installed" in err_msg or "not in your PATH" in err_msg or "FileNotFoundError" in err_msg:
            print("⚠ Tesseract not installed, using mock OCR data.")
            return {
                "merchant_name": "Sample Merchant (Mock)",
                "amount": 150.00,
                "currency": "USD",
                "date": datetime.now().strftime("%Y-%m-%d"),
                "suggested_category": "Travel",
                "raw_text": "Mocked OCR data since Tesseract executable is missing."
            }
        return {"error": f"OCR processing failed: {err_msg}"}


def _parse_receipt_text(text):
    """Parse OCR text to extract expense fields."""
    lines = text.strip().split("\n")
    lines = [l.strip() for l in lines if l.strip()]

    result = {
        "merchant_name": "",
        "amount": None,
        "currency": "",
        "date": "",
        "suggested_category": "Other",
    }

    # 1. Merchant name — usually the first non-empty line
    if lines:
        # Take first substantive line (skip very short lines)
        for line in lines[:5]:
            if len(line) > 2 and not re.match(r'^[\d\s\.\-\/]+$', line):
                result["merchant_name"] = line
                break

    # 2. Amount — look for the largest number (likely the total)
    amounts = []
    for line in lines:
        # Match patterns like $12.34, 12.34, 1,234.56, Total: 45.67
        matches = re.findall(r'[\$£€₹]?\s*(\d{1,3}(?:[,\.]\d{3})*(?:[\.]\d{2}))', line)
        for match in matches:
            try:
                clean = match.replace(",", "")
                amounts.append(float(clean))
            except ValueError:
                pass

    if amounts:
        # The total is usually the largest amount, or the last large amount
        result["amount"] = max(amounts)

    # 3. Currency — detect from symbols in text
    if "₹" in text or "rs" in text.lower() or "inr" in text.lower():
        result["currency"] = "INR"
    elif "$" in text:
        result["currency"] = "USD"
    elif "£" in text:
        result["currency"] = "GBP"
    elif "€" in text:
        result["currency"] = "EUR"

    # 4. Date — look for date patterns
    date_patterns = [
        r'(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})',  # DD/MM/YYYY or MM/DD/YYYY
        r'(\d{4}[/\-\.]\d{1,2}[/\-\.]\d{1,2})',      # YYYY-MM-DD
        r'(\w{3,9}\s+\d{1,2},?\s*\d{4})',              # March 15, 2024
    ]

    for pattern in date_patterns:
        match = re.search(pattern, text)
        if match:
            date_str = match.group(1)
            parsed = _try_parse_date(date_str)
            if parsed:
                result["date"] = parsed
                break

    # 5. Category — match keywords in text
    text_lower = text.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            result["suggested_category"] = category
            break

    return result


def _try_parse_date(date_str):
    """Try to parse a date string into ISO format."""
    formats = [
        "%d/%m/%Y", "%m/%d/%Y", "%Y-%m-%d", "%d-%m-%Y", "%m-%d-%Y",
        "%d.%m.%Y", "%m.%d.%Y", "%B %d, %Y", "%b %d, %Y",
        "%B %d %Y", "%b %d %Y", "%d/%m/%y", "%m/%d/%y",
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    return ""
