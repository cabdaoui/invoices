import os
import traceback
import logging
from pathlib import Path
from invoices.utils import load_env_config, ConfigError

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s - %(message)s")

REQUIRED_KEYS = [
    "EMAIL_ACCOUNT",
    "GMAIL_APP_PASSWORD",
    "INPUT_DIR",
    "TRAITEMENT_DIR",
    "OUTPUT_DIR",
    "EXCEL_FILE",
    "SMTP_SERVER",
    "SMTP_PORT",
    "EMAIL_RECIPIENTS",
    "EMAIL_SUBJECT",
    "EMAIL_BODY",
]

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

def _mkdirs(*dirs: Path):
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)

def _list_dir(d: Path, max_items: int = 50) -> str:
    if not d.exists():
        return f"{d} (n'existe pas)"
    items = []
    for i, p in enumerate(sorted(d.iterdir())):
        if i >= max_items:
            items.append("... (troncation)")
            break
        items.append(p.name + ("/" if p.is_dir() else ""))
    return f"{d} -> {', '.join(items) if items else '(vide)'}"

def _find_excel_anywhere(base: Path, filename: str) -> Path | None:
    # Cherche un fichier exact sous toute l’arborescence (coût OK pour un workspace Jenkins standard)
    candidates = list(base.rglob(filename))
    return candidates[0] if candidates else None

def _maybe_create_empty_report(path: Path):
    """Crée un Excel vide si autorisé par l'env (ALLOW_EMPTY_REPORT_IF_MISSING=true)."""
    from openpyxl import Workbook
    path.parent.mkdir(parents=True, exist_ok=True)
    wb = Workbook()
    ws = wb.active
    ws.title = "Reporting"
    ws.append(["Info"])  # minimal
    ws.append(["Fichier généré à blanc (fallback)."])
    wb.save(path)

def main():
    try:
        root = _project_root()
        env_path = root / "env.json"
        logging.info(f"Racine projet: {root}")
        logging.info(f"Chargement configuration depuis : {env_path}")

        env = load_env_config(path=str(env_path), required_keys=REQUIRED_KEYS)

        # Résolution des dossiers par rapport à la racine du projet/WORKSPACE
        input_dir = _resolve_dir(root, env.get("INPUT_DIR", "./input"))
        trait_dir = _resolve_dir(root, env.get("TRAITEMENT_DIR", "./traitement"))
        output_dir = _resolve_dir(root, env.get("OUTPUT_DIR", "./output"))
        _mkdirs(input_dir, trait_dir, output_dir)

        excel_name = env.get("EXCEL_FILE", "Reporting_invoices.xlsx")
        excel_file = output_dir / excel_name

        logging.info("Diagnostics dossiers :")
        logging.info(_list_dir(root))
        logging.info(_list_dir(output_dir))

        # 1) si le fichier est là, on envoie
        if not excel_file.exists():
            logging.warning(f"Reporting introuvable à l'endroit prévu: {excel_file}")

            # 2) fallback: recherche partout sous la racine/WORKSPACE
            found = _find_excel_anywhere(root, excel_name)
            if found:
                logging.info(f"Reporting trouvé ailleurs: {found}")
                excel_file = found

            else:
                # 3) optionnel: créer un Excel vide si autorisé
                allow_empty = str(env.get("ALLOW_EMPTY_REPORT_IF_MISSING", "")).lower() in ("1", "true", "yes")
                if allow_empty:
                    logging.warning("ALLOW_EMPTY_REPORT_IF_MISSING activé -> création d'un reporting vide.")
                    try:
                        _maybe_create_empty_report(excel_file)
                    except Exception as e:
                        logging.error(f"Echec de création du reporting vide: {e}")
                        raise FileNotFoundError(
                            f"Le reporting est manquant et la création automatique a échoué: {excel_file}"
                        ) from e
                else:
                    # 4) échoue avec message détaillé et listing
                    raise FileNotFoundError(
                        "Le reporting n'existe pas à l'endroit prévu et n'a pas été trouvé ailleurs.\n"
                        f"  Attendu : {excel_file}\n"
                        f"  Racine   : {root}\n"
                        f"  OUTPUT   : {_list_dir(output_dir)}\n"
                        "💡 Vérifie l'étape de génération du reporting (module/step Python qui crée l'Excel) "
                        "ou active ALLOW_EMPTY_REPORT_IF_MISSING=true dans env.json pour créer un fichier vide."
                    )

        # Envoi email
        import invoices.mail_sender as mail_sender
        logging.info(f"Envoi du reporting par email: {excel_file}")
        mail_sender.send_report(str(excel_file))

        logging.info("✅ Envoi du reporting terminé avec succès.")

    except ConfigError as e:
        logging.error(f"Erreur de configuration : {e}")
        raise
    except Exception:
        logging.error("Erreur critique dans le pipeline :\n%s", traceback.format_exc())
        raise

if __name__ == "__main__":
    main()
