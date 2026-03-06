from datetime import date
from generate_report import fetch_actual_cleanings, parse_date
from airbnb_normalize import fetch_and_normalize

def debug_cleaning_matching():
    bookings = fetch_and_normalize()
    cleanings = fetch_actual_cleanings()

    print("\n==============================")
    print("🔍 DEBUG MATCHING MÉNAGES")
    print("==============================\n")

    # Group cleanings by apartment
    cleanings_by_apartment = {}
    for c in cleanings:
        cleanings_by_apartment.setdefault(c["apartment"], []).append(c)

    for b in sorted(bookings, key=lambda x: (x["apartment"], x["checkout"])):
        apt = b["apartment"]
        checkout = b["checkout"]

        # Focus on the problematic window
        if checkout not in [
            date(2026, 2, 5),
            date(2026, 2, 9),
        ]:
            continue

        print("--------------------------------------------------")
        print(f"📦 Appartement : {apt}")
        print(f"🏁 Checkout (booking) : {checkout}  [{type(checkout)}]")

        found = False
        for c in cleanings_by_apartment.get(apt, []):
            print(
                f"   🧹 Cleaning raw date : {c['date']}  "
                f"[type={type(c['date'])}]"
            )
            if c["date"] == checkout:
                found = True
                print("      ✅ MATCH EXACT")

        if not found:
            print("      ❌ AUCUN MATCH")

    print("\n==============================")
    print("🔚 FIN DEBUG")
    print("==============================\n")


if __name__ == "__main__":
    debug_cleaning_matching()