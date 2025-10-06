# invoices/main.py
import os
import traceback
import logging
from pathlib import Path
from invoices.utils import load_env_config, ConfigError  # <-- import package explicite

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s - %(message)s"
)

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
    "EMAIL_BODY"
]

def main():
    try:
        # 🔑 On force le chemin recommandé : racine du projet / env.json
        package_dir = Path(__file__).resolve().parent           # .../invoices
        project_root = package_dir.parent                        # .../invoices_project
        env_path = project_root / "env.json"

        logging.info(f"Chargement configuration depuis : {env_path}")
        env = load_env_config(path=str(env_path), required_keys=REQUIRED_KEYS)

        # Chemin du fichier Excel attendu
        output_dir = env.get("OUTPUT_DIR", "./output")
        excel_name = env.get("EXCEL_FILE", "Reporting_invoices.xlsx")
        excel_file = Path(output_dir).resolve() / excel_name

        logging.info(f"Fichier Excel attendu : {excel_file}")
        if not excel_file.exists():
            raise FileNotFoundError(
                f"Le reporting n'existe pas à l'endroit prévu : {excel_file}. "
                "Vérifie la génération et la clé EXCEL_FILE/OUTPUT_DIR."
            )

        import invoices.mail_sender as mail_sender
        logging.info("Envoi du reporting par email ...")
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
