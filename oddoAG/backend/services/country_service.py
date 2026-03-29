"""Country and currency service using restcountries.com."""

import time
import requests

_country_cache = {"data": None, "fetched_at": 0}
CACHE_TTL = 3600  # 1 hour (country data rarely changes)


def get_countries():
    """Fetch all countries with their currencies, with caching."""
    now = time.time()

    if _country_cache["data"] and now - _country_cache["fetched_at"] < CACHE_TTL:
        return _country_cache["data"]

    try:
        url = "https://restcountries.com/v3.1/all?fields=name,currencies"
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        raw_data = response.json()

        countries = []
        for item in raw_data:
            name = item.get("name", {}).get("common", "")
            currencies = item.get("currencies", {})

            if not name or not currencies:
                continue

            # Get the first (primary) currency
            currency_code = list(currencies.keys())[0]
            currency_info = currencies[currency_code]

            countries.append({
                "name": name,
                "currency_code": currency_code,
                "currency_name": currency_info.get("name", ""),
                "currency_symbol": currency_info.get("symbol", ""),
            })

        # Sort by country name
        countries.sort(key=lambda c: c["name"])

        _country_cache["data"] = countries
        _country_cache["fetched_at"] = now
        return countries

    except Exception as e:
        print(f"✗ Countries API error: {e}")
        if _country_cache["data"]:
            return _country_cache["data"]
        # Minimal fallback
        return [
            {"name": "United States", "currency_code": "USD", "currency_name": "United States dollar", "currency_symbol": "$"},
            {"name": "United Kingdom", "currency_code": "GBP", "currency_name": "British pound", "currency_symbol": "£"},
            {"name": "India", "currency_code": "INR", "currency_name": "Indian rupee", "currency_symbol": "₹"},
            {"name": "European Union", "currency_code": "EUR", "currency_name": "Euro", "currency_symbol": "€"},
        ]
