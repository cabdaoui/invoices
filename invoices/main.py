# Script principal : pipeline factures
import os
import shutil
from invoices import mail_handler, pdf_parser, excel_reporter, mail_sender, logger_config

def main():
    logger = logger_config.setup_logger()

    logger.info("=== DÉMARRAGE DU PIPELINE FACTURES ===")

    try:
        # 1. Création des dossiers nécessaires
        input_dir = "./input"
        traitement_dir = "./traitement"
        output_dir = "./output"

        os.makedirs(input_dir, exist_ok=True)
        os.makedirs(traitement_dir, exist_ok=True)
        os.makedirs(output_dir, exist_ok=True)

        logger.info("Dossiers vérifiés/créés : ./input, ./traitement, ./output")

        # 2. Récupération des factures depuis la boîte mail
        logger.info("Récupération des factures depuis la boîte mail...")
        new_files = mail_handler.fetch_invoices()
        if new_files:
            logger.info(f"{len(new_files)} nouvelle(s) facture(s) récupérée(s) et stockée(s) dans ./input/")
        else:
            logger.info("Aucune nouvelle facture récupérée depuis la boîte mail.")

        # 3. Recherche des factures dans ./input/
        pdf_files = [
            os.path.join(input_dir, f)
            for f in os.listdir(input_dir)
            if f.lower().endswith(".pdf")
        ]

        if not pdf_files:
            logger.warning("Aucune facture trouvée dans ./input/.")
            return

        logger.info(f"{len(pdf_files)} facture(s) trouvée(s) dans ./input/.")

        # 4. Parsing des factures
        invoices_data = []
        for pdf_file in pdf_files:
            try:
                logger.info(f"Parsing de la facture : {pdf_file}")
                data = pdf_parser.extract_invoice_data(pdf_file)
                invoices_data.append(data)

                # ✅ Déplacer la facture traitée vers ./traitement/
                dest_path = os.path.join(traitement_dir, os.path.basename(pdf_file))
                shutil.move(pdf_file, dest_path)
                logger.info(f"Facture déplacée dans {dest_path}")

            except Exception as e:
                logger.error(f"Erreur lors du parsing de {pdf_file} : {e}")

        if not invoices_data:
            logger.error("Aucune donnée de facture extraite. Arrêt du processus.")
            return

        # 5. Génération du reporting Excel
        logger.info("Génération du fichier Excel...")
        excel_file = excel_reporter.generate_excel_report(invoices_data)
        logger.info(f"Reporting généré : {excel_file}")

        # 6. Envoi du reporting par mail
        logger.info("Envoi du reporting par mail...")
        mail_sender.send_report(excel_file)
        logger.info("Reporting envoyé avec succès ✅")

    except Exception as e:
        logger.exception(f"Erreur critique dans le pipeline : {e}")

    finally:
        logger.info("=== FIN DU PIPELINE FACTURES ===")


if __name__ == "__main__":
    main()
