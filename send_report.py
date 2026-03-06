import os
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# =====================================================
# CONFIGURATION
# =====================================================

REPORT_FILE = "rapport_menages.txt"
VERSION_TRACK_FILE = "email_version_tracker.txt"

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

# Credentials via environment variables
SENDER_EMAIL = os.getenv("GMAIL_SENDER")
SENDER_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")

CONTACTS = {
    "1": ("Antoine", "ant1.petruzzi@gmail.com"),
    "2": ("Melody", "melody.strambio@gmail.com"),
    "3": ("Pauline", "panoramic.concierge.services@gmail.com"),
    "4": ("Marine", "marinecotten35@gmail.com"),
}

EMAIL_SUBJECT_BASE = "Vérification dates de ménages"

# =====================================================
# VERSIONING
# =====================================================

def get_today_version():
    """
    Keeps track of how many emails were sent today
    so we can append v1, v2, v3…
    """
    today = datetime.now().strftime("%Y-%m-%d")

    if not os.path.exists(VERSION_TRACK_FILE):
        with open(VERSION_TRACK_FILE, "w") as f:
            f.write(f"{today}|1")
        return 1

    with open(VERSION_TRACK_FILE, "r") as f:
        content = f.read().strip()

    if not content:
        version = 1
    else:
        saved_date, saved_version = content.split("|")
        if saved_date == today:
            version = int(saved_version) + 1
        else:
            version = 1

    with open(VERSION_TRACK_FILE, "w") as f:
        f.write(f"{today}|{version}")

    return version

# =====================================================
# EMAIL SENDER
# =====================================================

def send_email(recipients, subject, body):
    if not SENDER_EMAIL or not SENDER_APP_PASSWORD:
        raise RuntimeError(
            "Identifiants Gmail manquants. "
            "Vérifie GMAIL_SENDER et GMAIL_APP_PASSWORD."
        )

    msg = MIMEMultipart()
    msg["From"] = SENDER_EMAIL
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject

    msg.attach(MIMEText(body, "plain", "utf-8"))

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_APP_PASSWORD)
        server.send_message(msg)

# =====================================================
# MAIN
# =====================================================

if __name__ == "__main__":
    # -----------------------------
    # Load report
    # -----------------------------
    if not os.path.exists(REPORT_FILE):
        raise RuntimeError(
            f"Fichier '{REPORT_FILE}' introuvable. "
            "Exécute d’abord generate_report.py."
        )

    with open(REPORT_FILE, "r", encoding="utf-8") as f:
        report = f.read().strip()

    if not report:
        print("⚠️ Rapport vide. Email annulé.")
        exit()

    # -----------------------------
    # Versioning
    # -----------------------------
    version = get_today_version()

    # -----------------------------
    # Timestamp line (FR)
    # -----------------------------
    now = datetime.now()
    header_line = (
        f"Email généré le {now.strftime('%d/%m/%Y')} "
        f"à {now.strftime('%H:%M')} — version v{version}\n\n"
    )

    # -----------------------------
    # Choose recipients
    # -----------------------------
    print("\nÀ qui envoyer le rapport ?\n")

    for key, (name, email) in CONTACTS.items():
        print(f"{key}. {name} ({email})")

    choix = input(
        "\nEntre les numéros séparés par des virgules "
        "(ex: 1,2 ou 1,3,4) : "
    )

    recipients = []
    for c in choix.split(","):
        c = c.strip()
        if c in CONTACTS:
            recipients.append(CONTACTS[c][1])

    if not recipients:
        print("❌ Aucun destinataire valide sélectionné. Envoi annulé.")
        exit()

    # -----------------------------
    # Confirmation
    # -----------------------------
    subject = f"{EMAIL_SUBJECT_BASE} — v{version}"

    print("\n----------------------------------------")
    print("EMAIL QUI VA ÊTRE ENVOYÉ")
    print("----------------------------------------")
    print(f"Sujet : {subject}\n")
    print(header_line + report)
    print("----------------------------------------")

    confirm = input("\nConfirmer l’envoi ? (o/n) : ").strip().lower()
    if confirm != "o":
        print("❌ Envoi annulé.")
        exit()

    # -----------------------------
    # Send
    # -----------------------------
    send_email(
        recipients=recipients,
        subject=subject,
        body=header_line + report
    )

    print(f"\n✅ Email envoyé avec succès (version v{version}).")










