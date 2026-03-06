import requests
import hashlib
from datetime import datetime
from icalendar import Calendar
import unicodedata


from google.oauth2 import service_account
from googleapiclient.discovery import build

# =====================================================
# CONFIG
# =====================================================

SERVICE_ACCOUNT_FILE = "service_account.json"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

DIRECT_SPREADSHEET_ID = "1R9T6MUhyNeKefdRoncz71k0vDK-nOrQk-e5pTnmejh4"
DIRECT_SHEET_NAME = "Form Responses 1"

# OTA CALENDAR SOURCES
APARTMENTS = {
    "GC-Studio-Haut": {
        "airbnb": [
            "https://www.airbnb.com/calendar/ical/1571199481935112281.ics?t=ab56147841c94db2be1f496e2d430d43"
        ]
    },
    "GC-T2": {
        "airbnb": [
            "https://www.airbnb.com/calendar/ical/1072702710038395847.ics?t=89b0650773d64811b307ca5490d139fa&locale=en"
        ],
        "booking": [
            "https://ical.booking.com/v1/export?t=445ae135-f5f8-4f82-9bbf-70f9be04bd48"
        ],
        "vrbo": [
            "http://www.vrbo.com/icalendar/33d985a30086492e8ed09a0fd55a47c0.ics"
        ],
    },
}

# =====================================================
# HELPERS
# =====================================================

def get_sheets_service():
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    return build("sheets", "v4", credentials=creds)

def normalize_uid(apartment, source, checkin, checkout):
    raw = f"{apartment}|{source}|{checkin}|{checkout}"
    return hashlib.md5(raw.encode()).hexdigest()

def to_date(val):
    if isinstance(val, datetime):
        return val.date()
    return val

# =====================================================
# OTA INGESTION
# =====================================================

def fetch_ical(url):
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    return Calendar.from_ical(resp.text)

def parse_event(event, apartment, source):
    dtstart = event.get("DTSTART")
    dtend = event.get("DTEND")

    if not dtstart or not dtend:
        return None

    checkin = to_date(dtstart.dt)
    checkout = to_date(dtend.dt)

    if checkout <= checkin:
        return None

    return {
        "apartment": apartment,
        "source": source,
        "checkin": checkin,
        "checkout": checkout,
        "booking_uid": normalize_uid(apartment, source, checkin, checkout),
    }

def fetch_ota_bookings(debug=False):
    bookings = []

    for apartment, sources in APARTMENTS.items():
        for source, urls in sources.items():
            for url in urls:
                try:
                    cal = fetch_ical(url)
                except Exception as e:
                    print(f"[WARN] Failed {apartment}/{source}: {e}")
                    continue

                for component in cal.walk():
                    if component.name != "VEVENT":
                        continue

                    booking = parse_event(component, apartment, source)
                    if not booking:
                        continue

                    bookings.append(booking)

                    if debug:
                        print(
                            f"[{apartment}][{source}] "
                            f"{booking['checkin']} → {booking['checkout']}"
                        )

    return bookings

# =====================================================
# DIRECT BOOKINGS (Google Form)
# =====================================================

def normalize_header(text):
    if not text:
        return ""
    text = text.strip()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return text.lower()

def parse_direct_date(raw):
    if not raw:
        return None

    raw = raw.strip()

    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue

    return None

def fetch_direct_bookings(debug=False):
    service = get_sheets_service()
    sheet = service.spreadsheets()

    rows = sheet.values().get(
        spreadsheetId=DIRECT_SPREADSHEET_ID,
        range=DIRECT_SHEET_NAME
    ).execute().get("values", [])

    if len(rows) < 2:
        return []

    raw_headers = rows[0]
    headers = [normalize_header(h) for h in raw_headers]
    data = rows[1:]

    bookings = []

    for row in data:
        record = dict(zip(headers, row))

        apartment = record.get("appartement")
        checkin_raw = record.get("date arrivee")
        checkout_raw = record.get("date depart")

        if not apartment or not checkin_raw or not checkout_raw:
            continue

        checkin = parse_direct_date(checkin_raw)
        checkout = parse_direct_date(checkout_raw)

        if not checkin or not checkout:
            continue

        if checkout <= checkin:
            continue

        booking = {
            "apartment": apartment.strip(),
            "source": "direct",
            "checkin": checkin,
            "checkout": checkout,
            "booking_uid": normalize_uid(apartment, "direct", checkin, checkout),
        }

        bookings.append(booking)

        if debug:
            print(f"[{apartment}][direct] {checkin} → {checkout}")

    return bookings

# =====================================================
# UNIFIED FETCH
# =====================================================

def fetch_and_normalize(debug=False):
    ota = fetch_ota_bookings(debug=debug)
    direct = fetch_direct_bookings(debug=debug)

    all_bookings = ota + direct

    # Deduplicate by apartment + checkout
    unique = {}
    for b in all_bookings:
        key = (b["apartment"], b["checkout"])
        unique[key] = b

    return list(unique.values())

# =====================================================
# DEBUG MODE
# =====================================================

if __name__ == "__main__":
    bookings = fetch_and_normalize(debug=True)
    print(f"\nTotal bookings: {len(bookings)}")
