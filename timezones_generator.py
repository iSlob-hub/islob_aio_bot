import requests
import json
import re
from typing import Optional

# === CONFIG ===
COUNTRIES_API = "https://restcountries.com/v3.1/all?fields=name,capital,timezones"
KYIV_OFFSET = 2.0  # Kyiv is UTC+2 (winter time) or UTC+3 (summer time), using winter

# Headers to avoid being blocked
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    'Accept': 'application/json'
}


def parse_utc_offset(tz_string: str) -> Optional[float]:
    """
    Parse UTC offset from string like 'UTC+02:00', 'UTC-05:00', or 'UTC'.
    Returns offset in hours as float, or None if parsing fails.
    """
    if tz_string == "UTC":
        return 0.0
    
    # Match patterns like UTC+02:00, UTC-05:30, etc.
    match = re.match(r'UTC([+-])(\d{1,2}):(\d{2})', tz_string)
    if not match:
        return None
    
    sign = 1 if match.group(1) == '+' else -1
    hours = int(match.group(2))
    minutes = int(match.group(3))
    
    return sign * (hours + minutes / 60.0)


def get_all_countries():
    """Fetch countries with capitals and timezones."""
    try:
        resp = requests.get(COUNTRIES_API, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        countries = []
        for c in resp.json():
            if "capital" in c and c["capital"] and "timezones" in c and c["timezones"]:
                # Get the first non-UTC timezone if available, or UTC if that's all there is
                tz = None
                for t in c["timezones"]:
                    if t != "UTC":
                        tz = t
                        break
                if not tz:
                    tz = c["timezones"][0]
                    
                countries.append({
                    "country": c["name"]["common"],
                    "capital": c["capital"][0],
                    "timezone": tz
                })
        return countries
    except Exception as e:
        print(f"Error fetching countries: {e}")
        return []


# Old hardcoded data for fallback (kept for reference)
TIMEZONE_TO_LOCATION_FALLBACK = {
    # Europe
    "Europe/London": {"country": "United Kingdom", "capital": "London"},
    "Europe/Paris": {"country": "France", "capital": "Paris"},
    "Europe/Berlin": {"country": "Germany", "capital": "Berlin"},
    "Europe/Rome": {"country": "Italy", "capital": "Rome"},
    "Europe/Madrid": {"country": "Spain", "capital": "Madrid"},
    "Europe/Amsterdam": {"country": "Netherlands", "capital": "Amsterdam"},
    "Europe/Brussels": {"country": "Belgium", "capital": "Brussels"},
    "Europe/Vienna": {"country": "Austria", "capital": "Vienna"},
    "Europe/Warsaw": {"country": "Poland", "capital": "Warsaw"},
    "Europe/Prague": {"country": "Czech Republic", "capital": "Prague"},
    "Europe/Budapest": {"country": "Hungary", "capital": "Budapest"},
    "Europe/Bucharest": {"country": "Romania", "capital": "Bucharest"},
    "Europe/Athens": {"country": "Greece", "capital": "Athens"},
    "Europe/Stockholm": {"country": "Sweden", "capital": "Stockholm"},
    "Europe/Oslo": {"country": "Norway", "capital": "Oslo"},
    "Europe/Copenhagen": {"country": "Denmark", "capital": "Copenhagen"},
    "Europe/Helsinki": {"country": "Finland", "capital": "Helsinki"},
    "Europe/Dublin": {"country": "Ireland", "capital": "Dublin"},
    "Europe/Lisbon": {"country": "Portugal", "capital": "Lisbon"},
    "Europe/Zurich": {"country": "Switzerland", "capital": "Zurich"},
    "Europe/Kiev": {"country": "Ukraine", "capital": "Kyiv"},
    "Europe/Moscow": {"country": "Russia", "capital": "Moscow"},
    "Europe/Istanbul": {"country": "Turkey", "capital": "Istanbul"},
    
    # Americas
    "America/New_York": {"country": "USA", "capital": "New York (EST)"},
    "America/Chicago": {"country": "USA", "capital": "Chicago (CST)"},
    "America/Denver": {"country": "USA", "capital": "Denver (MST)"},
    "America/Los_Angeles": {"country": "USA", "capital": "Los Angeles (PST)"},
    "America/Toronto": {"country": "Canada", "capital": "Toronto"},
    "America/Vancouver": {"country": "Canada", "capital": "Vancouver"},
    "America/Mexico_City": {"country": "Mexico", "capital": "Mexico City"},
    "America/Bogota": {"country": "Colombia", "capital": "Bogota"},
    "America/Lima": {"country": "Peru", "capital": "Lima"},
    "America/Santiago": {"country": "Chile", "capital": "Santiago"},
    "America/Buenos_Aires": {"country": "Argentina", "capital": "Buenos Aires"},
    "America/Sao_Paulo": {"country": "Brazil", "capital": "São Paulo"},
    "America/Caracas": {"country": "Venezuela", "capital": "Caracas"},
    
    # Asia
    "Asia/Tokyo": {"country": "Japan", "capital": "Tokyo"},
    "Asia/Seoul": {"country": "South Korea", "capital": "Seoul"},
    "Asia/Shanghai": {"country": "China", "capital": "Shanghai"},
    "Asia/Beijing": {"country": "China", "capital": "Beijing"},
    "Asia/Hong_Kong": {"country": "Hong Kong", "capital": "Hong Kong"},
    "Asia/Singapore": {"country": "Singapore", "capital": "Singapore"},
    "Asia/Bangkok": {"country": "Thailand", "capital": "Bangkok"},
    "Asia/Ho_Chi_Minh": {"country": "Vietnam", "capital": "Ho Chi Minh City"},
    "Asia/Jakarta": {"country": "Indonesia", "capital": "Jakarta"},
    "Asia/Manila": {"country": "Philippines", "capital": "Manila"},
    "Asia/Kuala_Lumpur": {"country": "Malaysia", "capital": "Kuala Lumpur"},
    "Asia/Dubai": {"country": "UAE", "capital": "Dubai"},
    "Asia/Riyadh": {"country": "Saudi Arabia", "capital": "Riyadh"},
    "Asia/Tel_Aviv": {"country": "Israel", "capital": "Tel Aviv"},
    "Asia/Kolkata": {"country": "India", "capital": "Kolkata"},
    "Asia/Karachi": {"country": "Pakistan", "capital": "Karachi"},
    "Asia/Dhaka": {"country": "Bangladesh", "capital": "Dhaka"},
    "Asia/Almaty": {"country": "Kazakhstan", "capital": "Almaty"},
    "Asia/Tashkent": {"country": "Uzbekistan", "capital": "Tashkent"},
    "Asia/Yerevan": {"country": "Armenia", "capital": "Yerevan"},
    "Asia/Baku": {"country": "Azerbaijan", "capital": "Baku"},
    "Asia/Tbilisi": {"country": "Georgia", "capital": "Tbilisi"},
    
    # Oceania
    "Australia/Sydney": {"country": "Australia", "capital": "Sydney"},
    "Australia/Melbourne": {"country": "Australia", "capital": "Melbourne"},
    "Australia/Perth": {"country": "Australia", "capital": "Perth"},
    "Pacific/Auckland": {"country": "New Zealand", "capital": "Auckland"},
    "Pacific/Fiji": {"country": "Fiji", "capital": "Suva"},
    
    # Africa
    "Africa/Cairo": {"country": "Egypt", "capital": "Cairo"},
    "Africa/Johannesburg": {"country": "South Africa", "capital": "Johannesburg"},
    "Africa/Lagos": {"country": "Nigeria", "capital": "Lagos"},
    "Africa/Nairobi": {"country": "Kenya", "capital": "Nairobi"},
    "Africa/Casablanca": {"country": "Morocco", "capital": "Casablanca"},
    "Africa/Algiers": {"country": "Algeria", "capital": "Algiers"},
    "Africa/Tunis": {"country": "Tunisia", "capital": "Tunis"},
}


def main():
    print("="*60)
    print("Timezone Offsets Generator")
    print("="*60)
    print("\nFetching data from REST Countries API...")
    
    # Kyiv offset is fixed
    print(f"\n1. Using Kyiv offset: UTC{KYIV_OFFSET:+.1f}h")
    
    # Get all countries
    print("\n2. Fetching countries with capitals and timezones...")
    countries = get_all_countries()
    if not countries:
        print("❌ Failed to fetch countries.")
        return
    print(f"   ✓ Found {len(countries)} countries with capitals")
    
    print("\n3. Calculating timezone offsets...")
    print("-"*60)
    
    result = []
    processed = 0
    failed = 0

    for idx, c in enumerate(countries, 1):
        country = c["country"]
        capital = c["capital"]
        tz_string = c["timezone"]
        
        print(f"[{idx:3}/{len(countries)}] {country:30} ({capital:20}) {tz_string}")
        
        offset = parse_utc_offset(tz_string)
        if offset is None:
            print(f"      ⚠️  Failed to parse timezone: {tz_string}")
            failed += 1
            continue

        diff = round(offset - KYIV_OFFSET, 1)
        result.append({
            "country": country,
            "capital": capital,
            "timezone": tz_string,
            "utc_offset": round(offset, 1),
            "offset_from_kyiv": diff
        })
        processed += 1

    # Sort by offset from Kyiv
    result.sort(key=lambda x: x["offset_from_kyiv"])

    with open("time_offsets.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print("-"*60)
    print(f"\n{'='*60}")
    print(f"✅ Successfully processed: {processed} countries")
    print(f"❌ Failed: {failed} countries")
    print("💾 Saved to: time_offsets.json")
    print(f"{'='*60}")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
