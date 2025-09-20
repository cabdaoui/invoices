# Gestion de la boîte mail
import imaplib
import email
import os
import json

def load_env():
    with open(os.path.join("env", "env.json"), encoding="utf-8") as f:
        return json.load(f)

def fetch_invoices():
    env = load_env()
    imap = imaplib.IMAP4_SSL("imap.gmail.com")
    imap.login(env["EMAIL_ACCOUNT"], env["GMAIL_APP_PASSWORD"])
    imap.select("INBOX")

    status, messages = imap.search(None, '(UNSEEN SUBJECT "Facture")')
    invoices = []

    if status == "OK":
        for num in messages[0].split():
            status, data = imap.fetch(num, "(RFC822)")
            msg = email.message_from_bytes(data[0][1])
            for part in msg.walk():
                if part.get_content_type() == "application/pdf":
                    filename = part.get_filename()
                    if filename:
                        filepath = os.path.join(env["INPUT_DIR"], filename)
                        with open(filepath, "wb") as f:
                            f.write(part.get_payload(decode=True))
                        invoices.append(filepath)
    imap.close()
    imap.logout()
    return invoices
