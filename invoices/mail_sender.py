# invoices/mail_sender.py
import os
import mimetypes
import smtplib
from email.message import EmailMessage
from pathlib import Path
from typing import List
from invoices.utils import load_env_config, ConfigError  # import via package

def normalize_recipients(val) -> List[str]:
    """Accepte une liste ou une chaîne séparée par des virgules, nettoie et déduplique."""
    if not val:
        return []
    if isinstance(val, list):
        items = val
    else:
        items = str(val).split(",")
    cleaned: List[str] = []
    seen = set()
    for x in items:
        addr = str(x).strip()
        if addr and addr.lower() not in seen:
            cleaned.append(addr)
            seen.add(addr.lower())
    return cleaned

def _attach_file(msg: EmailMessage, file_path: str | os.PathLike):
    p = Path(file_path)
    if not p.exists():
        raise FileNotFoundError(f"Pièce jointe introuvable: {p}")
    ctype, encoding = mimetypes.guess_type(str(p))
    if ctype is None or encoding is not None:
        ctype = "application/octet-stream"
    maintype, subtype = ctype.split("/", 1)
    with p.open("rb") as f:
        msg.add_attachment(f.read(), maintype=maintype, subtype=subtype, filename=p.name)

def send_report(excel_file: str):
    """
    Envoie le reporting par email en lisant la configuration depuis env.json (déjà validée par main).
    Supporte EMAIL_RECIPIENTS, EMAIL_CC, EMAIL_BCC (liste ou chaîne).
    SMTP_SSL (465) par défaut, STARTTLS si SMTP_USE_STARTTLS=true.
    """
    env = load_env_config()

    account = env["EMAIL_ACCOUNT"]
    app_pass = env["GMAIL_APP_PASSWORD"]
    smtp_server = env.get("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(env.get("SMTP_PORT", 465))
    use_starttls = str(env.get("SMTP_USE_STARTTLS", "")).lower() in ("1", "true", "yes")
    subject = env.get("EMAIL_SUBJECT", "Reporting")
    body = env.get("EMAIL_BODY", "")

    to_list = normalize_recipients(env.get("EMAIL_RECIPIENTS", ""))
    cc_list = normalize_recipients(env.get("EMAIL_CC", ""))
    bcc_list = normalize_recipients(env.get("EMAIL_BCC", ""))

    if not to_list and not cc_list and not bcc_list:
        raise ConfigError("Aucun destinataire: EMAIL_RECIPIENTS/EMAIL_CC/EMAIL_BCC sont vides.")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = account
    if to_list:
        msg["To"] = ", ".join(to_list)
    if cc_list:
        msg["Cc"] = ", ".join(cc_list)
    # Bcc n'apparaît pas dans les en-têtes visibles
    msg["Reply-To"] = account
    msg.set_content(body)

    _attach_file(msg, excel_file)

    all_rcpts = to_list + cc_list + bcc_list

    if use_starttls:
        # STARTTLS (ex: smtp.gmail.com:587)
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(account, app_pass)
            server.send_message(msg, from_addr=account, to_addrs=all_rcpts)
    else:
        # SSL direct (ex: smtp.gmail.com:465)
        with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
            server.login(account, app_pass)
            server.send_message(msg, from_addr=account, to_addrs=all_rcpts)
