"""Currency conversion service using exchangerate-api.com."""

import time
import requests

# In-memory cache: { base_currency: { rates: {...}, fetched_at: timestamp } }
_rate_cache = {}
CACHE_TTL = 900  # 15 minutes


def get_exchange_rates(base_currency):
    """Fetch exchange rates for a base currency, with caching."""
    base = base_currency.upper()
    now = time.time()

    # Check cache
    if base in _rate_cache:
        cached = _rate_cache[base]
        if now - cached["fetched_at"] < CACHE_TTL:
            return cached["rates"]

    try:
        url = f"https://api.exchangerate-api.com/v4/latest/{base}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        rates = data.get("rates", {})
        _rate_cache[base] = {"rates": rates, "fetched_at": now}
        return rates

    except Exception as e:
        print(f"✗ Currency API error: {e}")
        # Return cached data even if stale
        if base in _rate_cache:
            return _rate_cache[base]["rates"]
        return None


def convert_currency(amount, from_currency, to_currency):
    """Convert an amount from one currency to another."""
    if from_currency.upper() == to_currency.upper():
        return amount

    rates = get_exchange_rates(from_currency.upper())
    if not rates:
        return None

    target_rate = rates.get(to_currency.upper())
    if not target_rate:
        return None

    return round(amount * target_rate, 2)


def get_all_currencies():
    """Get a list of all available currency codes."""
    rates = get_exchange_rates("USD")
    if rates:
        return sorted(rates.keys())
    # Fallback to common currencies
    return [
        "AED", "ARS", "AUD", "BRL", "CAD", "CHF", "CNY", "CZK", "DKK",
        "EUR", "GBP", "HKD", "HUF", "IDR", "ILS", "INR", "JPY", "KRW",
        "MXN", "MYR", "NOK", "NZD", "PHP", "PLN", "RUB", "SAR", "SEK",
        "SGD", "THB", "TRY", "TWD", "USD", "ZAR",
    ]
