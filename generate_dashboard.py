from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo

from airbnb_normalize import fetch_and_normalize
from generate_report import (
    fetch_actual_cleanings,
    parse_date_with_context,
    REPORT_WINDOW_DAYS,
)

OUTPUT_FILE = "dashboard/index.html"

# =====================================================

def format_date(d):
    return d.strftime("%d-%m-%Y")

def format_time(t):
    return t.strftime("%H:%M") if t else ""

# =====================================================

def build_dashboard(bookings, cleanings):
    today = date.today()
    horizon = today + timedelta(days=REPORT_WINDOW_DAYS)

    cleanings_by_apartment = {}
    for c in cleanings:
        cleanings_by_apartment.setdefault(c["apartment"], []).append(c)

    bookings_by_apartment = {}
    for b in bookings:
        checkout = b["checkout"]
        if checkout < today or checkout > horizon:
            continue
        bookings_by_apartment.setdefault(b["apartment"], []).append(b)

    sxm_now = datetime.now(ZoneInfo("America/Puerto_Rico"))
    updated = sxm_now.strftime("%d/%m/%Y %H:%M")

    html = f"""
    <html>
    <head>
    <meta charset="UTF-8">
    <title>SXM Cleaning Dashboard</title>

    <style>
    body {{
        font-family: Arial, sans-serif;
        margin: 40px;
        background: #f5f5f5;
        color: #222;
    }}

    h1 {{
        margin-bottom: 5px;
    }}

    h2 {{
        margin-top: 40px;
        margin-bottom: 10px;
        border-bottom: 2px solid #333;
        padding-bottom: 6px;
    }}

    table {{
        border-collapse: collapse;
        width: 100%;
        background: white;
        margin-bottom: 20px;
    }}

    th, td {{
        border: 1px solid #ddd;
        padding: 10px;
        text-align: center;
    }}

    th {{
        background: #333;
        color: white;
    }}

    .ok {{
        background: #d4edda;
    }}

    .missing {{
        background: #f8d7da;
    }}

    .muted {{
        color: #666;
        font-size: 14px;
    }}
    </style>
    </head>

    <body>
    <h1>SXM Cleaning Dashboard</h1>
    <p class="muted">Mis à jour : {updated}</p>
    """

    for apartment in sorted(bookings_by_apartment):
        html += f"<h2>{apartment}</h2>"
        html += """
        <table>
        <tr>
            <th>Checkout</th>
            <th>Date ménage</th>
            <th>Heure</th>
            <th>Cleaner</th>
            <th>Statut</th>
        </tr>
        """

        apartment_cleanings = cleanings_by_apartment.get(apartment, [])

        for b in sorted(bookings_by_apartment[apartment], key=lambda x: x["checkout"]):
            checkout = b["checkout"]
            matched_cleaning = None

            # Reuse same intelligent date resolution as generate_report.py
            for c in apartment_cleanings:
                resolved = parse_date_with_context(c["raw_date"], checkout)
                if resolved == checkout:
                    matched_cleaning = c.copy()
                    matched_cleaning["date"] = resolved
                    break

            if matched_cleaning:
                start = format_time(matched_cleaning["time_start"])
                end = format_time(matched_cleaning["time_end"])

                if start and end:
                    time_str = f"{start}–{end}"
                else:
                    time_str = ""

                html += f"""
                <tr class="ok">
                    <td>{format_date(checkout)}</td>
                    <td>{format_date(matched_cleaning["date"])}</td>
                    <td>{time_str or '—'}</td>
                    <td>{matched_cleaning["person"] or '—'}</td>
                    <td>OK</td>
                </tr>
                """
            else:
                html += f"""
                <tr class="missing">
                    <td>{format_date(checkout)}</td>
                    <td>—</td>
                    <td>—</td>
                    <td>—</td>
                    <td>Manquant</td>
                </tr>
                """

        html += "</table>"

    html += "</body></html>"
    return html

# =====================================================

if __name__ == "__main__":
    bookings = fetch_and_normalize()
    cleanings = fetch_actual_cleanings()

    html = build_dashboard(bookings, cleanings)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Dashboard generated → {OUTPUT_FILE}")