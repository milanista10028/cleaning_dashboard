import requests
from ics import Calendar

ICAL_URL = "https://www.airbnb.com/calendar/ical/1571199481935112281.ics?t=ab56147841c94db2be1f496e2d430d43"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/calendar,text/plain,*/*"
}

response = requests.get(ICAL_URL, headers=headers, timeout=15)
response.raise_for_status()

calendar = Calendar(response.text)

for event in calendar.events:
    print(event.uid, event.begin.date(), event.end.date())
