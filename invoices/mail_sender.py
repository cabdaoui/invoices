# mail_sender.py
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

from utils import load_env_config, normalize_recipients

def send_report(excel_path: str):
    # 1) Vérif du fichier joint
    if not os.path.isabs(excel_path):
        excel_path = os.path.abspath(excel_path)
    if not os.path.exists(excel_path):
        raise FileNotFoundError(f"Fichier Excel introuvable: {excel_path}")

    # 2) Config
    env = load_env_config()  # lit ton env.json
    sender = env["EMAIL_ACCOUNT"]
    recipients = normalize_recipients(env)
    if not recipients:
        raise ValueError("Aucun destinataire (EMAIL_RECIPIENTS/RECIPIENT_EMAILS).")

    # 3) Message
    msg = MIMEMultipart()
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = env.get("EMAIL_SUBJECT", "Reporting")
    body = env.get("EMAIL_BODY", "Bonjour,\nVeuillez trouver ci-joint le reporting.")
    msg.attach(MIMEText(body, "plain", "utf-8"))

    with open(excel_path, "rb") as f:
        part = MIMEApplication(f.read(), _subtype="xlsx")
        part.add_header("Content-Disposition", "attachment",
                        filename=os.path.basename(excel_path))
        msg.attach(part)

    # 4) SMTP
    smtp_server = env.get("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(env.get("SMTP_PORT", 465))
    app_password = env["GMAIL_APP_PASSWORD"]

    if smtp_port == 465:
        with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
            server.login(sender, app_password)
            server.sendmail(sender, recipients, msg.as_string())
    else:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender, app_password)
            server.sendmail(sender, recipients, msg.as_string())
