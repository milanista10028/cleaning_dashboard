from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build

from airbnb_normalize import fetch_and_normalize

# =====================================================
# CONFIGURATION
# =====================================================

SERVICE_ACCOUNT_FILE = "service_account.json"

CALENDAR_ID = "primary"  # or a dedicated calendar ID if you use one

SCOPES = ["https://www.googleapis.com/auth/calendar"]

# =====================================================
# GOOGLE CALENDAR CLIENT
# =====================================================

def get_calendar_service():
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    return build("calendar", "v3", credentials=creds)

# =====================================================
# EVENT BUILDER
# =====================================================

def build_event(booking):
    start_date = booking["checkin"].isoformat()
    end_date = booking["checkout"].isoformat()

    apartment = booking["apartment"]
    source = booking["source"]

    return {
        "summary": f"[{apartment}] Séjour locataire",
        "description": (
            f"Appartement : {apartment}\n"
            f"Source : {source}\n"
            f"UID : {booking['booking_uid']}"
        ),
        "start": {"date": start_date},
        "end": {"date": end_date},
        "extendedProperties": {
            "private": {
                "booking_uid": booking["booking_uid"],
                "apartment": apartment,
                "source": source,
            }
        },
    }

# =====================================================
# SYNC LOGIC
# =====================================================

def sync_bookings_to_gcal():
    service = get_calendar_service()
    bookings = fetch_and_normalize()

    # -------------------------------------------------
    # Fetch existing calendar events (NO server-side filter)
    # -------------------------------------------------
    events = service.events().list(
        calendarId=CALENDAR_ID,
        maxResults=2500,
        singleEvents=True,
    ).execute().get("items", [])

    # Build map of existing booking_uids → event_id
    existing = {}
    for e in events:
        props = e.get("extendedProperties", {}).get("private", {})
        uid = props.get("booking_uid")
        if uid:
            existing[uid] = e["id"]

    created = 0
    skipped = 0

    # -------------------------------------------------
    # Create missing events
    # -------------------------------------------------
    for booking in bookings:
        uid = booking["booking_uid"]

        if uid in existing:
            skipped += 1
            continue

        event = build_event(booking)

        service.events().insert(
            calendarId=CALENDAR_ID,
            body=event
        ).execute()

        created += 1

    print(
        f"✅ Sync terminé — "
        f"{created} événement(s) créé(s), "
        f"{skipped} déjà présent(s)."
    )

# =====================================================
# MAIN
# =====================================================

if __name__ == "__main__":
    sync_bookings_to_gcal()