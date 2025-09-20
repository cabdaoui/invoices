# Parsing PDF et extraction regex
import pdfplumber
import re

def extract_invoice_data(pdf_path):
    data = {}
    with pdfplumber.open(pdf_path) as pdf:
        text = ""
        for page in pdf.pages:
            text += page.extract_text() or ""

    # Exemple de regex (montant et date)
    montant = re.search(r"Montant[:\s]+([\d,\.]+)", text)
    date = re.search(r"Date[:\s]+(\d{2}/\d{2}/\d{4})", text)

    data["fichier"] = pdf_path
    data["montant"] = montant.group(1) if montant else "N/A"
    data["date"] = date.group(1) if date else "N/A"

    return data
