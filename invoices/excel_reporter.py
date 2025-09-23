import os
import datetime
import openpyxl
from invoices.config_loader import load_env  # ✅ fonctionne si config_loader.py existe

def generate_excel_report(invoices_data):
    """
    Génère un fichier Excel dans ./output avec un nom basé sur la date :
    Reportingdd_mm_yy.xlsx
    Retourne le chemin complet du fichier généré.
    """
    env = load_env()
    output_dir = "./output"
    os.makedirs(output_dir, exist_ok=True)

    # Génération du nom du fichier avec la date du jour
    today_str = datetime.datetime.now().strftime("%d_%m_%y")
    excel_filename = f"Reporting_{today_str}.xlsx"
    excel_path = os.path.join(output_dir, excel_filename)

    # Création du fichier Excel
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Factures"
    ws.append(["Facture", "Montant", "Date"])

    for inv in invoices_data:
        ws.append([inv.get("facture"), inv.get("montant"), inv.get("date")])

    wb.save(excel_path)
    return excel_path
