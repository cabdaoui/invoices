import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
import os
import datetime
from invoices.config_loader import load_env  # import centralisé

def send_report(report_path):
    """
    Envoie par mail le fichier Excel généré dans ./output.
    """
    env = load_env()
    sender = env["EMAIL_ACCOUNT"]
    recipient = env["RECIPIENT_EMAIL"]   # ✅ correction ici
    password = env["GMAIL_APP_PASSWORD"]

    # Sujet avec la date
    today_str = datetime.datetime.now().strftime("%d/%m/%y")
    subject = f"{env.get('EMAIL_SUBJECT', 'Reporting Factures')} - {today_str}"

    # Création du message
    msg = MIMEMultipart()
    msg["From"] = sender
    msg["To"] = recipient
    msg["Subject"] = subject

    # Corps du mail
    body = env.get("EMAIL_BODY", "Veuillez trouver ci-joint le reporting des factures.")
    msg.attach(MIMEText(body, "plain"))

    # Attacher le fichier Excel
    with open(report_path, "rb") as f:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f'attachment; filename="{os.path.basename(report_path)}"')
        msg.attach(part)

    # Envoi via SMTP Gmail
    with smtplib.SMTP_SSL(env["SMTP_SERVER"], env["SMTP_PORT"]) as server:
        server.login(sender, password)
        server.send_message(msg)

    print(f"✅ Rapport envoyé à {recipient} avec pièce jointe {os.path.basename(report_path)}")
