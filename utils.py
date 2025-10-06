# utils.py
import json
from pathlib import Path
from typing import Iterable, Mapping, Any

class ConfigError(RuntimeError):
    """Erreur de configuration levée lorsque le fichier env.json est invalide ou incomplet."""
    pass


def load_env_config(path: str = "env.json", required_keys: Iterable[str] | None = None) -> Mapping[str, Any]:
    """
    Charge le fichier env.json et valide les clés obligatoires.
    :param path: chemin du fichier JSON d'environnement
    :param required_keys: liste des clés obligatoires à vérifier
    :return: dictionnaire des variables de configuration
    """
    p = Path(path)

    if not p.exists():
        raise ConfigError(f"Fichier de configuration introuvable : {p.resolve()}")

    try:
        cfg = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ConfigError(f"JSON invalide dans {p.resolve()} : {e}") from e

    # Clés à valider : priorité à la liste passée, sinon celles dans le JSON
    required = list(required_keys or cfg.get("_required_keys") or [])

    if required:
        missing = [k for k in required if k not in cfg or cfg.get(k) in (None, "", [])]
        if missing:
            # ✅ ICI était ton bug : il manquait le guillemet fermant après {', '.join(missing)}
            raise ConfigError(f"Clés manquantes/vides dans env.json : {', '.join(missing)}")

    return cfg
