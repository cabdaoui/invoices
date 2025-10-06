# utils.py
import json
from pathlib import Path
from typing import Iterable, Mapping, Any

class ConfigError(RuntimeError):
    pass

def load_env_config(path: str = "env.json", required_keys: Iterable[str] | None = None) -> Mapping[str, Any]:
    p = Path(path)
    if not p.exists():
        raise ConfigError(f"Fichier de config introuvable: {p.resolve()}")
    try:
        cfg = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ConfigError(f"JSON invalide dans {p.resolve()}: {e}") from e

    # priorité: paramètre > champ _required_keys dans le fichier > pas de validation
    required = list(required_keys or cfg.get("_required_keys") or [])
    if required:
        missing = [k for k in required if k not in cfg or cfg.get(k) in (None, "", [])]
        if missing:
            raise ConfigError(f"Clés manquantes/vides dans env.json:
