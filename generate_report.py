from datetime import datetime, date, timedelta
import unicodedata

from google.oauth2 import service_account
from googleapiclient.discovery import build

from airbnb_normalize import fetch_and_normalize

# =====================================================
# CONFIGURATION
# =====================================================

SERVICE_ACCOUNT_FILE = "service_account.json"

SPREADSHEET_ID = "1NXeHyvwtl-T3T5mhOkbmsXcEEDyx_AQAkF7g5kgtNlw"
SHEET_NAME = "Form Responses 1"

SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

OUTPUT_FILE = "rapport_menages.txt"

REPORT_WINDOW_DAYS = 180

# =====================================================
# GOOGLE SHEETS
# =====================================================

def get_sheets_service():
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    return build("sheets", "v4", credentials=creds)

# =====================================================
# NORMALISATION & PARSING
# =====================================================

def normalize(text):
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = "".join(c for c in text if not c.isspace())
    return text.lower()

def parse_date_basic(raw):
    if not raw:
        return None
    raw = raw.strip()
    for fmt in ("%d/%m/%Y", "%m/%d/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None

def parse_date_with_context(raw, reference_date):
    if not raw or not reference_date:
        return None

    raw = raw.strip()
    candidates = []

    for fmt in ("%d/%m/%Y", "%m/%d/%Y"):
        try:
            candidates.append(datetime.strptime(raw, fmt).date())
        except ValueError:
            pass

    try:
        candidates.append(datetime.strptime(raw, "%Y-%m-%d").date())
    except ValueError:
        pass

    if not candidates:
        return None

    candidates.sort(key=lambda d: abs((d - reference_date).days))
    return candidates[0]

def parse_time(raw):
    if not raw:
        return None
    raw = raw.strip()

    for fmt in ("%H:%M", "%H:%M:%S", "%I:%M %p", "%I:%M:%S %p"):
        try:
            return datetime.strptime(raw, fmt).time()
        except ValueError:
            continue
    return None

def format_date_fr(d):
    return d.strftime("%d-%m-%Y")

def format_time_fr(t):
    return t.strftime("%H:%M") if t else None

def normalize_apartment(raw):
    raw = (raw or "").lower()
    if "studio" in raw:
        return "GC-Studio-Haut"
    if "t2" in raw:
        return "GC-T2"
    return None

# =====================================================
# FETCH CLEANINGS (GOOGLE FORM)
# =====================================================

def fetch_actual_cleanings():
    service = get_sheets_service()
    sheet = service.spreadsheets()

    rows = sheet.values().get(
        spreadsheetId=SPREADSHEET_ID,
        range=SHEET_NAME
    ).execute().get("values", [])

    if len(rows) < 2:
        return []

    headers = rows[0]
    data = rows[1:]

    normalized_headers = {normalize(h): h for h in headers}

    apt_col = next(v for k, v in normalized_headers.items() if "appartement" in k)
    date_col = next(v for k, v in normalized_headers.items() if "date" in k and "menage" in k)
    person_col = next((v for k, v in normalized_headers.items() if "personne" in k), None)
    start_col = next((v for k, v in normalized_headers.items() if "heuredebut" in k), None)
    end_col = next((v for k, v in normalized_headers.items() if "heurefin" in k), None)

    cleanings = []

    for row in data:
        record = dict(zip(headers, row))

        apartment = normalize_apartment(record.get(apt_col))
        if not apartment:
            continue

        raw_date = record.get(date_col)
        parsed_date = parse_date_basic(raw_date)
        if not parsed_date:
            continue

        cleanings.append({
            "apartment": apartment,
            "raw_date": raw_date,
            "date": parsed_date,
            "time_start": parse_time(record.get(start_col)) if start_col else None,
            "time_end": parse_time(record.get(end_col)) if end_col else None,
            "person": record.get(person_col, "").strip() if person_col else ""
        })

    return cleanings

# =====================================================
# REPORT GENERATION
# =====================================================

def build_french_audit_report(bookings, cleanings):
    today = date.today()
    horizon = today + timedelta(days=REPORT_WINDOW_DAYS)

    lignes = []

    cleanings_by_apartment = {}
    for c in cleanings:
        cleanings_by_apartment.setdefault(c["apartment"], []).append(c)

    bookings_by_apartment = {}
    for b in bookings:
        checkout = b["checkout"]
        if checkout < today or checkout > horizon:
            continue
        bookings_by_apartment.setdefault(b["apartment"], []).append(b)

    for apartment in sorted(bookings_by_apartment.keys()):
        lignes.append("=" * 30)
        lignes.append(f"APPARTEMENT : {apartment.upper()}")
        lignes.append("=" * 30)
        lignes.append("")

        apartment_bookings = sorted(
            bookings_by_apartment[apartment],
            key=lambda x: x["checkout"]
        )

        apartment_cleanings = cleanings_by_apartment.get(apartment, [])

        for b in apartment_bookings:
            sortie = b["checkout"]
            nettoyage = None

            for c in apartment_cleanings:
                resolved = parse_date_with_context(c["raw_date"], sortie)
                if resolved == sortie:
                    nettoyage = c
                    nettoyage["date"] = resolved
                    break

            lignes.append(f"Sortie locataire : {format_date_fr(sortie)}")

            if nettoyage:
                heure = ""
                if nettoyage["time_start"] and nettoyage["time_end"]:
                    heure = (
                        f" || Heure : "
                        f"{format_time_fr(nettoyage['time_start'])}"
                        f"–{format_time_fr(nettoyage['time_end'])}"
                    )

                lignes.append(
                    f"Ménage planifié : OUI"
                    f" || Date : {format_date_fr(nettoyage['date'])}"
                    f"{heure}"
                    f" || Par : {nettoyage['person'] or '—'}"
                )
            else:
                lignes.append("Ménage planifié : ❌ NON")

            lignes.append("")

        lignes.append("")

    return "\n".join(lignes).strip()

# =====================================================
# MAIN
# =====================================================

if __name__ == "__main__":
    bookings = fetch_and_normalize()
    cleanings = fetch_actual_cleanings()

    report = build_french_audit_report(bookings, cleanings)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"✅ Rapport généré : {OUTPUT_FILE}\n")
    print(report)
