# invoices/mail_sender.py
import os
import mimetypes
import smtplib
from email.message import EmailMessage
from pathlib import Path
from typing import List, Optional

from invoices.utils import load_env_config, ConfigError  # import via package

# Nom de fichier autorisé (verrouillage)
ALLOWED_EXCEL_NAME = "invoices_extract.xlsx"


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
    # (Conservé mais non utilisé, au cas où — peut être supprimé)
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
    # Sécurité: n’autoriser que invoices_extract.xlsx
    if p.name != ALLOWED_EXCEL_NAME:
        raise ConfigError(f"Seul le fichier '{ALLOWED_EXCEL_NAME}' est autorisé en pièce jointe (reçu: '{p.name}').")

    ctype, encoding = mimetypes.guess_type(str(p))
    if ctype is None or encoding is not None:
        ctype = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" if p.suffix.lower() == ".xlsx" \
                else "application/octet-stream"
    maintype, subtype = ctype.split("/", 1)
    with p.open("rb") as f:
        msg.add_attachment(f.read(), maintype=maintype, subtype=subtype, filename=p.name)


# ---------------------------
# Résolution stricte du fichier Excel
# ---------------------------

def _resolve_excel_path_from_env(env: dict) -> Path:
    """
    Renvoie le chemin de 'invoices_extract.xlsx' UNIQUEMENT :
      - si EXCEL_FILE est défini, il doit s'appeler exactement 'invoices_extract.xlsx'
      - sinon on cherche 'invoices_extract.xlsx' dans OUTPUT_DIR
    Échec sinon.
    """
    root = _project_root()
    output_dir = _resolve_dir(root, env.get("OUTPUT_DIR", "./output"))

    preferred_name = env.get("EXCEL_FILE", "").strip()
    # Si EXCEL_FILE est renseigné, il doit être le nom autorisé
    if preferred_name:
        pref = Path(preferred_name).name  # normaliser sur le nom
        if pref != ALLOWED_EXCEL_NAME:
            raise ConfigError(
                f"EXCEL_FILE doit être '{ALLOWED_EXCEL_NAME}' (actuel: '{pref}')."
            )
        p = (output_dir / ALLOWED_EXCEL_NAME).resolve()
        if p.exists():
            return p
        # S'il ne se trouve pas dans OUTPUT_DIR, tenter tel quel si chemin absolu
        abs_try = Path(preferred_name)
        if abs_try.is_absolute() and abs_try.exists() and abs_try.name == ALLOWED_EXCEL_NAME:
            return abs_try.resolve()

    # Sinon, chercher strictement 'invoices_extract.xlsx' dans OUTPUT_DIR
    p = (output_dir / ALLOWED_EXCEL_NAME).resolve()
    if p.exists():
        return p

    # Échec — rien d'autre n'est autorisé
    raise FileNotFoundError(
        "Aucun fichier autorisé trouvé à envoyer.\n"
        f"  OUTPUT_DIR: {output_dir}\n"
        f"  Requis    : {ALLOWED_EXCEL_NAME}\n"
        "💡 Vérifie que le reporting a bien été généré avec ce nom exact."
    )


# ---------------------------
# Envoi principal
# ---------------------------

def send_report(excel_file: Optional[str] = None):
    """
    Envoie le reporting par email en lisant la configuration depuis env.json.
    ⚠️ Restriction: seule la pièce jointe 'invoices_extract.xlsx' est autorisée.
    Règles:
      - Si 'excel_file' est fourni, il doit s'appeler exactement 'invoices_extract.xlsx'.
      - Sinon, on résout via OUTPUT_DIR et (optionnellement) EXCEL_FILE s'il est conforme.
    Supporte EMAIL_RECIPIENTS, EMAIL_CC, EMAIL_BCC (liste ou chaîne).
    SMTP_SSL (465) par défaut, STARTTLS si SMTP_USE_STARTTLS=true.
    """
    env = load_env_config()

    # Détermination du fichier Excel à joindre (verrouillé)
    if excel_file:
        excel_path = Path(excel_file).resolve()
        if excel_path.name != ALLOWED_EXCEL_NAME:
            raise ConfigError(
                f"Argument excel_file non autorisé: seul '{ALLOWED_EXCEL_NAME}' peut être envoyé "
                f"(reçu: '{excel_path.name}')."
            )
        if not excel_path.exists():
            # On retombe sur la résolution stricte depuis l'env
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
