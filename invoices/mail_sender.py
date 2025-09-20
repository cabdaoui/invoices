# Envoi d'email
import smtplib, ssl, os, json
from email.message import EmailMessage

def load_env():
    with open(os.path.join("env", "env.json"), encoding="utf-8") as f:
        return json.load(f)

def send_report(report_file):
    env = load_env()
    msg = EmailMessage()
    msg["From"] = env["EMAIL_ACCOUNT"]
    msg["To"] = env["RECIPIENT_EMAIL"]
    msg["Subject"] = env["EMAIL_SUBJECT"]
    msg.set_content(env["EMAIL_BODY"])

    with open(report_file, "rb") as f:
        msg.add_attachment(f.read(), maintype="application", subtype="octet-stream", filename=os.path.basename(report_file))

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(env["SMTP_SERVER"], env["SMTP_PORT"], context=context) as server:
        server.login(env["EMAIL_ACCOUNT"], env["GMAIL_APP_PASSWORD"])
        server.send_message(msg)

