import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

def send_report(excel_path: str):
    env = load_env_config_somehow()  # ta fonction existante qui charge le JSON

    sender = env["EMAIL_ACCOUNT"]
    recipients = _normalize_recipients(env)  # <-- corrige l'erreur ici

    msg = MIMEMultipart()
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = env.get("EMAIL_SUBJECT", "Reporting")

    body = env.get("EMAIL_BODY", "Bonjour,\nVeuillez trouver ci-joint le reporting.")
    msg.attach(MIMEText(body, "plain", "utf-8"))

    # pièce jointe
    with open(excel_path, "rb") as f:
        part = MIMEApplication(f.read(), _subtype="xlsx")
        part.add_header("Content-Disposition", "attachment", filename=os.path.basename(excel_path))
        msg.attach(part)

    smtp_server = env.get("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(env.get("SMTP_PORT", 465))
    app_password = env["GMAIL_APP_PASSWORD"]

    if smtp_port == 465:
        # SSL direct (Gmail)
        with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
            server.login(sender, app_password)
            server.sendmail(sender, recipients, msg.as_string())
    else:
        # STARTTLS (ex. port 587)
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender, app_password)
            server.sendmail(sender, recipients, msg.as_string())
