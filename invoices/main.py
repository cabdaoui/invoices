# main.py
import os
import traceback
import logging

logging.basicConfig(level=logging.INFO,
    format="%(asctime)s %(levelname)s - %(message)s")

def main():
    try:
        # ... ton code qui génère le fichier ...
        # Suppose que tu as EXCEL_FILE dans env.json et que le fichier est en ./output
        from utils import load_env_config
        env = load_env_config()
        excel_name = env.get("EXCEL_FILE", "Reporting_invoices.xlsx")
        excel_file = os.path.abspath(os.path.join("output", excel_name))

        logging.info(f"Fichier Excel attendu: {excel_file}")
        if not os.path.exists(excel_file):
            raise FileNotFoundError(
                f"Le reporting n'existe pas à l'endroit prévu: {excel_file}. "
                f"Vérifie la génération dans ./output et la clé EXCEL_FILE."
            )

        import mail_sender
        mail_sender.send_report(excel_file)

        logging.info("Envoi du reporting terminé avec succès.")

    except Exception:
        logging.error("Erreur critique dans le pipeline :\n%s",
                      traceback.format_exc())
        raise  # laisse Jenkins marquer le job en échec

if __name__ == "__main__":
    main()
