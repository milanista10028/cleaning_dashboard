import requests
from datetime import datetime, timedelta
from icalendar import Calendar
import hashlib

# =====================================================
# APARTMENT + ICAL CONFIG
# =====================================================

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
            "https://ical.booking.com/v1/export?t=bc8dad7a-ee86-4af7-8abd-243156f45e59"
        ],
        "vrbo": [
            "http://www.vrbo.com/icalendar/33d985a30086492e8ed09a0fd55a47c0.ics"
        ],
    },
}

# =====================================================
# HELPERS
# =====================================================

def fetch_ical(url):
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    return Calendar.from_ical(resp.text)

def to_date(val):
    if isinstance(val, datetime):
        return val.date()
    return val

def normalize_uid(apartment, source, uid):
    raw = f"{apartment}|{source}|{uid}"
    return hashlib.md5(raw.encode()).hexdigest()

# =====================================================
# ICAL NORMALIZATION
# =====================================================

def parse_event(event, apartment, source):
    dtstart = event.get("DTSTART")
    dtend = event.get("DTEND")

    if not dtstart or not dtend:
        return None

    checkin = to_date(dtstart.dt)
    checkout = to_date(dtend.dt)

    # Ignore zero-night or invalid bookings
    if checkout <= checkin:
        return None

    uid = event.get("UID", "")
    booking_uid = normalize_uid(apartment, source, uid)

    return {
        "apartment": apartment,
        "source": source,
        "checkin": checkin,
        "checkout": checkout,
        "booking_uid": booking_uid,
    }

# =====================================================
# MAIN INGESTION
# =====================================================

def fetch_and_normalize(debug=False):
    bookings = []

    for apartment, sources in APARTMENTS.items():
        for source, urls in sources.items():
            for url in urls:
                try:
                    cal = fetch_ical(url)
                except Exception as e:
                    print(f"[WARN] Failed to fetch {apartment} / {source}: {e}")
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

    # De-duplicate by apartment + checkout date
    unique = {}
    for b in bookings:
        key = (b["apartment"], b["checkout"])
        unique[key] = b

    return list(unique.values())
