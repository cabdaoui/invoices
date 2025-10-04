# utils.py
import json
import os
from typing import Dict, Any, List

REQUIRED_KEYS = ["EMAIL_ACCOUNT", "GMAIL_APP_PASSWORD"]

def _load_from_json(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def _load_from_environ() -> Dict[str, Any]:
    # récupère toutes les variables pertinentes depuis l'environnement Jenkins
    keys = [
        "EMAIL_ACCOUNT", "GMAIL_APP_PASSWORD", "EMAIL_RECIPIENTS",
        "EMAIL_SUBJECT", "EMAIL_BODY", "SMTP_SERVER", "SMTP_PORT"
    ]
    cfg = {k: os.environ.get(k) for k in keys if os.environ.get(k) is not None}
    return cfg

def load_env_config(path: str = "env.json") -> Dict[str, Any]:
    """
    Charge la config depuis env.json si présent, sinon depuis les variables d'environnement.
    Priorité au JSON si disponible.
    """
    cfg = {}
    if os.path.exists(path):
        cfg = _load_from_json(path)
    else:
        cfg = _load_from_environ()

    # valeurs par défaut raisonnables
    cfg.setdefault("SMTP_SERVER", "smtp.gmail.com")
    cfg.setdefault("SMTP_PORT", 465)
    cfg.setdefault("EMAIL_SUBJECT", "Reporting")
    cfg.setdefault("EMAIL_BODY", "Bonjour,\nVeuillez trouver ci-joint le reporting.")

    # validation minimale
    missing = [k for k in REQUIRED_KEYS if k not in cfg or not cfg[k]]
    if missing:
        raise KeyError(
            f"Missing required config keys: {missing}. "
            f"Provide them in env.json or as environment variables."
        )
    return cfg

def normalize_recipients(env: Dict[str, Any]) -> List[str]:
    """
    Retourne une liste d'emails à partir de EMAIL_RECIPIENTS (string 'a@b.com,c@d.com' ou liste).
    """
    rec = env.get("EMAIL_RECIPIENTS", [])
    if isinstance(rec, str):
        return [r.strip() for r in rec.split(",") if r.strip()]
    if isinstance(rec, list):
        return [str(r).strip() for r in rec if str(r).strip()]
    return []
