from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo

from airbnb_normalize import fetch_and_normalize
from generate_report import (
    fetch_actual_cleanings,
    parse_date_with_context,
    REPORT_WINDOW_DAYS,
)

OUTPUT_FILE = "dashboard/index.html"


FORM_BASE_URL = "https://docs.google.com/forms/d/e/1FAIpQLSdBN4n07N_xvPtpuAi4N_-NwjQK7NuEEfF4LtZM5pAJ_byILw/viewform?usp=header"

FORM_FIELDS = {
    "Appartement": "entry.735473369",
    "date de menage": "entry.1999453291"
}

# =====================================================

def format_date(d):
    return d.strftime("%d-%m-%Y")

def format_time(t):
    return t.strftime("%H:%M") if t else ""

# =====================================================

def build_form_link(apartment, checkout_date, action="Planifier un ménage"):

    date_str = checkout_date.strftime("%Y-%m-%d")

    url = (
        f"{FORM_BASE_URL}"
        f"&{FORM_FIELDS['apartment']}={apartment}"
        f"&{FORM_FIELDS['date']}={date_str}"
    )

    return url

    # =====================================================

def build_dashboard(bookings, cleanings):

    cleanings_by_apartment = {}

    for c in cleanings:
        cleanings_by_apartment.setdefault(c["apartment"], []).append(c)

    bookings_by_apartment = {}

    for b in bookings:
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
        font-family: Arial;
        margin: 40px;
        background:#f5f5f5;
    }}

    h1 {{
        margin-bottom:5px;
    }}

    h2 {{
        margin-top:40px;
    }}

    table {{
        border-collapse: collapse;
        width:100%;
        background:white;
    }}

    th, td {{
        border:1px solid #ddd;
        padding:10px;
        text-align:center;
    }}

    th {{
        background:#333;
        color:white;
    }}

    .ok {{
        background:#d4edda;
    }}

    .missing {{
        background:#f8d7da;
    }}

    .btn {{
        background:#2b7cff;
        color:white;
        padding:6px 10px;
        border-radius:4px;
        text-decoration:none;
        font-size:13px;
    }}

    </style>
    </head>

    <body>

    <h1>SXM Cleaning Dashboard</h1>
    <p>Mis à jour : {updated}</p>
    """

    for apartment in sorted(bookings_by_apartment):

        html += f"<h2>{apartment}</h2>"
        html += """
        <table>
        <tr>
        <th>Checkout</th>
        <th>Cleaning date</th>
        <th>Cleaner</th>
        <th>Action</th>
        </tr>
        """

        apartment_cleanings = cleanings_by_apartment.get(apartment, [])

        for b in sorted(bookings_by_apartment[apartment], key=lambda x: x["checkout"]):

            checkout = b["checkout"]

            cleaning = next(
                (c for c in apartment_cleanings if c["date"] == checkout),
                None
            )

            # Prefilled form link
            form_link = build_form_link(apartment, checkout)

            if cleaning:

                start = format_time(cleaning["time_start"])
                end = format_time(cleaning["time_end"])

                time_str = f"{start}-{end}" if start else ""

                html += f"""
                <tr class="ok">
                <td>{format_date(checkout)}</td>
                <td>{format_date(cleaning["date"])} {time_str}</td>
                <td>{cleaning["person"]}</td>
                <td>
                <a href="{form_link}" target="_blank" class="btn">
                Modifier
                </a>
                </td>
                </tr>
                """

            else:

                html += f"""
                <tr class="missing">
                <td>{format_date(checkout)}</td>
                <td>-</td>
                <td>-</td>
                <td>
                <a href="{form_link}" target="_blank" class="btn">
                Planifier / Modifier
                </a>
                </td>
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