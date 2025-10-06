# invoices/utils.py
import json
import os
from pathlib import Path
from typing import Iterable, Mapping, Any, Optional, List

class ConfigError(RuntimeError):
    """Erreur de configuration levée lorsque le fichier env.json est invalide ou introuvable."""
    pass

def _candidate_env_paths(explicit: Optional[str]) -> List[Path]:
    """
    Construit une liste d'emplacements candidats pour env.json, par ordre de priorité.
    """
    candidates: List[Path] = []
    if explicit:
        candidates.append(Path(explicit))

    # 1) Variable d'env pour override complet
    env_override = os.environ.get("INVOICES_ENV_PATH")
    if env_override:
        candidates.append(Path(env_override))

    # 2) Dossier du module utils.py (invoices/)
    here = Path(__file__).resolve().parent
    candidates.append(here / "env.json")

    # 3) Racine du projet (parent de invoices/)
    project_root = here.parent
    candidates.append(project_root / "env.json")

    # 4) Répertoire courant (utile si on lance depuis ailleurs)
    cwd = Path.cwd()
    candidates.append(cwd / "env.json")

    # 5) WORKSPACE Jenkins (si défini)
    workspace = os.environ.get("WORKSPACE")
    if workspace:
        candidates.append(Path(workspace) / "env.json")

    # Dédupli
    uniq = []
    seen = set()
    for p in candidates:
        rp = str(p.resolve()) if p.exists() else str(p)
        if rp not in seen:
            uniq.append(p)
            seen.add(rp)
    return uniq

def load_env_config(path: Optional[str] = None, required_keys: Iterable[str] | None = None) -> Mapping[str, Any]:
    """
    Charge env.json depuis l'un des chemins candidats et valide les clés requises.
    - path : chemin explicite optionnel
    - required_keys : liste des clés obligatoires
    """
    candidates = _candidate_env_paths(path)
    for cand in candidates:
        if cand.exists():
            try:
                data = json.loads(cand.read_text(encoding="utf-8"))
            except json.JSONDecodeError as e:
                raise ConfigError(f"JSON invalide dans {cand.resolve()} : {e}") from e

            required = list(required_keys or data.get("_required_keys") or [])
            if required:
                missing = [k for k in required if k not in data or data.get(k) in (None, "", [])]
                if missing:
                    raise ConfigError(
                        f"Clés manquantes/vides dans {cand.resolve()} : {', '.join(missing)}"
                    )
            return data

    # Rien trouvé : message clair avec la liste des chemins testés
    tested = "\n - ".join(str(p) for p in candidates)
    raise ConfigError(
        "Fichier de configuration introuvable. Chemins testés :\n - " + tested +
        "\n\n💡 Solutions :\n"
        "  1) Place env.json à la racine du projet (même niveau que le dossier 'invoices').\n"
        "  2) Ou passe un chemin explicite à load_env_config(path=...).\n"
        "  3) Ou définis INVOICES_ENV_PATH dans l'environnement Jenkins/Windows."
    )
