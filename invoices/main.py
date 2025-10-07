# invoices/main.py
import os
import traceback
import logging
from pathlib import Path

from invoices.utils import load_env_config, ConfigError
from invoices.pdf_parser import extract_invoice_data
from invoices.excel_reporter import write_report

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
    candidates = list(base.rglob(filename))
    return candidates[0] if candidates else None

def main():
    try:
        # 1) Chargement config + dossiers
        root = _project_root()
        env_path = root / "env.json"
        logging.info(f"Racine projet: {root}")
        logging.info(f"Chargement configuration depuis : {env_path}")

        env = load_env_config(path=str(env_path), required_keys=REQUIRED_KEYS)

        input_dir = _resolve_dir(root, env.get("INPUT_DIR", "./input"))
        trait_dir = _resolve_dir(root, env.get("TRAITEMENT_DIR", "./traitement"))
        output_dir = _resolve_dir(root, env.get("OUTPUT_DIR", "./output"))
        _mkdirs(input_dir, trait_dir, output_dir)

        excel_name = env.get("EXCEL_FILE", "Reporting_invoices.xlsx")
        excel_file = output_dir / excel_name

        logging.info("Diagnostics dossiers :")
        logging.info(_list_dir(root))
        logging.info(_list_dir(input_dir))
        logging.info(_list_dir(output_dir))

        # 2) Parcours des PDF + extraction via pdf_parser (regex only)
        pdf_paths = sorted(list(input_dir.rglob("*.pdf")))
        rows: list[dict] = []

        if not pdf_paths:
            logging.warning(f"Aucun PDF trouvé dans {input_dir}")

        for pdf in pdf_paths:
            try:
                logging.info(f"Extraction: {pdf}")
                data = extract_invoice_data(str(pdf))
                # data contient: fichier, facture, date, total_ttc, periode, source_montant
                rows.append(data)

                # (Optionnel) déplacer le PDF traité :
                # (trait_dir / pdf.name).write_bytes(pdf.read_bytes()); pdf.unlink()

            except Exception as e:
                logging.error(f"Échec extraction {pdf}: {e}")

        # 3) Écriture du reporting Excel (aligné excel_reporter/pdf_parser)
        if rows:
            write_report(rows, excel_file)
            logging.info(f"Reporting généré: {excel_file} ({len(rows)} ligne(s))")
        else:
            allow_empty = str(env.get("ALLOW_EMPTY_REPORT_IF_MISSING", "")).lower() in ("1", "true", "yes")
            if allow_empty:
                logging.warning("Aucune donnée extraite, création d'un reporting vide (ALLOW_EMPTY_REPORT_IF_MISSING=true).")
                write_report([], excel_file)
            else:
                raise FileNotFoundError(
                    "Aucune facture PDF traitée -> pas de reporting généré.\n"
                    f"  Dossier INPUT : {_list_dir(input_dir)}\n"
                    "💡 Ajoute des PDF dans INPUT, ou active ALLOW_EMPTY_REPORT_IF_MISSING=true dans env.json."
                )

        # Double vérif au cas où
        if not excel_file.exists():
            logging.warning(f"Reporting introuvable à l'endroit prévu: {excel_file}")
            found = _find_excel_anywhere(root, excel_name)
            if found:
                logging.info(f"Reporting trouvé ailleurs: {found}")
                excel_file = found
            else:
                raise FileNotFoundError(
                    "Le reporting n'existe pas à l'endroit prévu et n'a pas été trouvé ailleurs.\n"
                    f"  Attendu : {excel_file}\n"
                    f"  Racine   : {root}\n"
                    f"  OUTPUT   : {_list_dir(output_dir)}\n"
                    "💡 Vérifie la génération du reporting ou active ALLOW_EMPTY_REPORT_IF_MISSING=true."
                )

        # 4) Envoi email
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
