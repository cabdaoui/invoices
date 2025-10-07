# invoices/mail_sender.py
import os
import mimetypes
import smtplib
from email.message import EmailMessage
from pathlib import Path
from typing import List, Optional

from invoices.utils import load_env_config, ConfigError  # import via package


# ---------------------------
# Helpers chemins & fichiers
# ---------------------------

def _project_root() -> Path:
    """Racine du projet: parent de invoices/ ou WORKSPACE Jenkins si défini."""
    package_dir = Path(__file__).resolve().parent          # .../invoices
    ws = os.environ.get("WORKSPACE")
    if ws:
        return Path(ws).resolve()
    return package_dir.parent                               # .../invoices_project

def _resolve_dir(base: Path, value: str) -> Path:
    p = Path(value)
    return (base / p).resolve() if not p.is_absolute() else p.resolve()

def _latest_xlsx_in(dir_path: Path) -> Optional[Path]:
    if not dir_path.exists():
        return None
    xlsxs = sorted(dir_path.glob("*.xlsx"), key=lambda p: p.stat().st_mtime, reverse=True)
    return xlsxs[0] if xlsxs else None


# ---------------------------
# Helpers email
# ---------------------------

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
        ctype = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" if p.suffix.lower() == ".xlsx" \
                else "application/octet-stream"
    maintype, subtype = ctype.split("/", 1)
    with p.open("rb") as f:
        msg.add_attachment(f.read(), maintype=maintype, subtype=subtype, filename=p.name)


# ---------------------------
# Envoi principal
# ---------------------------

def _resolve_excel_path_from_env(env: dict) -> Path:
    """Construit le chemin du fichier Excel à partir de env.json, avec fallbacks intelligents."""
    root = _project_root()
    output_dir = _resolve_dir(root, env.get("OUTPUT_DIR", "./output"))
    preferred_name = env.get("EXCEL_FILE", "").strip()

    # 1) Nom préféré depuis env.json
    if preferred_name:
        p = (output_dir / preferred_name).resolve()
        if p.exists():
            return p

    # 2) Fallbacks usuels
    for candidate in ("invoices_extract.xlsx", "Reporting_invoices.xlsx"):
        p = (output_dir / candidate).resolve()
        if p.exists():
            return p

    # 3) Dernier .xlsx modifié dans OUTPUT_DIR
    latest = _latest_xlsx_in(output_dir)
    if latest:
        return latest.resolve()

    # 4) Rien trouvé
    raise FileNotFoundError(
        "Aucun fichier Excel (.xlsx) trouvé à envoyer.\n"
        f"  OUTPUT_DIR: {output_dir}\n"
        f"  EXCEL_FILE: {preferred_name or '(non défini)'}\n"
        "💡 Vérifie que le reporting a bien été généré dans OUTPUT_DIR."
    )


def send_report(excel_file: Optional[str] = None):
    """
    Envoie le reporting par email en lisant la configuration depuis env.json.
    Si excel_file n'est pas fourni, on récupère automatiquement le fichier .xlsx dans OUTPUT_DIR :
      - EXCEL_FILE (env.json) si présent
      - sinon 'invoices_extract.xlsx'
      - sinon 'Reporting_invoices.xlsx'
      - sinon le .xlsx le plus récent dans OUTPUT_DIR
    Supporte EMAIL_RECIPIENTS, EMAIL_CC, EMAIL_BCC (liste ou chaîne).
    SMTP_SSL (465) par défaut, STARTTLS si SMTP_USE_STARTTLS=true.
    """
    env = load_env_config()

    # Détermination du fichier Excel à joindre
    if excel_file:
        excel_path = Path(excel_file).resolve()
        if not excel_path.exists():
            # Si le chemin fourni n'existe pas, tente les fallbacks dans OUTPUT_DIR
            excel_path = _resolve_excel_path_from_env(env)
    else:
        excel_path = _resolve_excel_path_from_env(env)

    account = env["EMAIL_ACCOUNT"]
    app_pass = env["GMAIL_APP_PASSWORD"]
    smtp_server = env.get("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(env.get("SMTP_PORT", 465))
    use_starttls = str(env.get("SMTP_USE_STARTTLS", "")).lower() in ("1", "true", "yes")
    subject = env.get("EMAIL_SUBJECT", f"Reporting factures - {excel_path.name}")
    body = env.get("EMAIL_BODY", f"Veuillez trouver ci-joint le reporting: {excel_path.name}")

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

    _attach_file(msg, excel_path)

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
