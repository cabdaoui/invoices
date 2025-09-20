# Génération Excel
import os
import json
import openpyxl

def load_env():
    with open(os.path.join("env", "env.json"), encoding="utf-8") as f:
        return json.load(f)

def generate_excel_report(invoices_data):
    env = load_env()
    output_file = os.path.join(env["TRAITEMENT_DIR"], env["EXCEL_FILE"])

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Invoices"

    # En-têtes
    ws.append(["Fichier", "Montant", "Date"])

    for inv in invoices_data:
        ws.append([inv["fichier"], inv["montant"], inv["date"]])

    wb.save(output_file)
    return output_file

