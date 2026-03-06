import sys
import traceback

from airbnb_normalize import fetch_and_normalize
from sync_bookings_to_gcal import sync_bookings_to_gcal
from generate_report import build_french_audit_report, fetch_actual_cleanings
from generate_report import OUTPUT_FILE
from generate_report import format_date_fr

# =====================================================
# ORCHESTRATOR
# =====================================================

def run_pipeline():
    print("\n==============================")
    print("🚀 DÉMARRAGE PIPELINE SXM")
    print("==============================\n")

    try:
        # -------------------------------------------------
        # 1️⃣ FETCH & NORMALIZE BOOKINGS
        # -------------------------------------------------
        print("1️⃣ Chargement des réservations (Airbnb / Booking / VRBO)…")
        bookings = fetch_and_normalize(debug=True)
        print(f"   ✔ {len(bookings)} réservations chargées\n")

        # -------------------------------------------------
        # 2️⃣ SYNC BOOKINGS → GOOGLE CALENDAR
        # -------------------------------------------------
        print("2️⃣ Synchronisation des réservations vers Google Calendar…")
        sync_bookings_to_gcal()
        print("   ✔ Synchronisation terminée\n")

        # -------------------------------------------------
        # 3️⃣ FETCH ACTUAL CLEANINGS
        # -------------------------------------------------
        print("3️⃣ Chargement des ménages déclarés (Google Form)…")
        cleanings = fetch_actual_cleanings()
        print(f"   ✔ {len(cleanings)} ménages trouvés\n")

        # -------------------------------------------------
        # 4️⃣ GENERATE REPORT
        # -------------------------------------------------
        print("4️⃣ Génération du rapport de contrôle des ménages…")
        report = build_french_audit_report(bookings, cleanings)

        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(report)

        print(f"   ✔ Rapport généré : {OUTPUT_FILE}\n")

        # -------------------------------------------------
        # 5️⃣ SUMMARY (QUICK SANITY)
        # -------------------------------------------------
        missing = report.count("❌ NON")
        print("📊 RÉSUMÉ")
        print(f"   • Ménages manquants : {missing}")
        print("\n🎯 Pipeline terminé avec succès.\n")

    except Exception as e:
        print("\n❌ ERREUR DANS LE PIPELINE\n")
        traceback.print_exc()
        sys.exit(1)


# =====================================================
# MAIN
# =====================================================

if __name__ == "__main__":
    run_pipeline()
