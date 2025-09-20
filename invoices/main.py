# Script principal
import os
from invoices import mail_handler, pdf_parser, excel_reporter, mail_sender, logger_config

def main():
    logger = logger_config.setup_logger()

    logger.info("=== DÉMARRAGE DU PIPELINE FACTURES ===")

    try:
        # 1. Récupération des factures depuis la boîte mail
        logger.info("Récupération des factures depuis la boîte mail...")
        pdf_files = mail_handler.fetch_invoices()
        if not pdf_files:
            logger.warning("Aucune nouvelle facture trouvée dans la boîte mail.")
            return
        logger.info(f"{len(pdf_files)} facture(s) récupérée(s).")

        # 2. Parsing des factures
        invoices_data = []
        for pdf_file in pdf_files:
            try:
                logger.info(f"Parsing de la facture : {pdf_file}")
                data = pdf_parser.extract_invoice_data(pdf_file)
                invoices_data.append(data)
            except Exception as e:
                logger.error(f"Erreur lors du parsing de {pdf_file} : {e}")

        if not invoices_data:
            logger.error("Aucune donnée de facture extraite. Arrêt du processus.")
            return

        # 3. Génération du reporting Excel
        logger.info("Génération du fichier Excel...")
        excel_file = excel_reporter.generate_excel_report(invoices_data)
        logger.info(f"Reporting généré : {excel_file}")

        # 4. Envoi du reporting par mail
        logger.info("Envoi du reporting par mail...")
        mail_sender.send_report(excel_file)
        logger.info("Reporting envoyé avec succès ✅")

    except Exception as e:
        logger.exception(f"Erreur critique dans le pipeline : {e}")

    finally:
        logger.info("=== FIN DU PIPELINE FACTURES ===")

if __name__ == "__main__":
    main()
