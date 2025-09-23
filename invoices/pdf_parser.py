import re
import pdfplumber

def extract_invoice_data(pdf_path):
    """
    Extrait les informations principales d'une facture PDF :
    - Numéro de facture (Facture N°xxxx)
    - Date (ex. 'le 01/07/2024')
    - Montant (ex. 'Total TTC* 286,00€')
    """
    invoice_number = None
    amount = None
    date = None

    try:
        with pdfplumber.open(pdf_path) as pdf:
            text = ""
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                text += page_text + "\n"

        # 🔎 Numéro de facture
        match = re.search(r"Facture\s*N°\s*([A-Za-z0-9\-\_/]+)", text, re.IGNORECASE)
        if match:
            invoice_number = match.group(1)

        # 🔎 Date après "le " (ex. "Team Alan, le 01/07/2024")
        match_date = re.search(r"le\s+(\d{2}/\d{2}/\d{4})", text, re.IGNORECASE)
        if match_date:
            date = match_date.group(1)

        # 🔎 Montant après "Total TTC"
        match_amount = re.search(r"Total\s*TTC\*?\s*pour\s+[A-Za-zéû]+\s+\d{4}\s*([\d\s.,]+)\s*([€$]?)", text, re.IGNORECASE)
        if match_amount:
            amount_value = match_amount.group(1).replace(" ", "")
            currency = match_amount.group(2) or ""
            amount = f"{amount_value}{currency}"

    except Exception as e:
        print(f"❌ Erreur lors de l'extraction du PDF {pdf_path} : {e}")

    return {
        "facture": invoice_number if invoice_number else "INCONNU",
        "date": date if date else "INCONNU",
        "montant": amount if amount else "INCONNU"
    }
