# invoices/pdf_parser.py
from __future__ import annotations

import re
from pathlib import Path
from typing import Optional, Dict, Any

import pdfplumber

__all__ = [
    "extract_invoice_data",
    "extract_invoice_number_from_string",
    "find_invoice_number",
    "find_date",
    "find_amount_total_ttc_star",
    "find_amount_generic",
]

# ============================
#   REGEX UNIQUEMENT
# ============================

# 1) Numéro de facture
#   - "Facture N°..."
#   - "Nº ...", "No ...", "N° ..."
#   - "Invoice No./Number/# ..."
RGX_INVOICE = [
    re.compile(r"(?i)\bfacture\s*(?:n[°ºo]\s*)?[:#]?\s*([A-Za-z0-9._/\-]+)"),
    re.compile(r"(?i)\bn[°ºo]\s*[:#]?\s*([A-Za-z0-9._/\-]+)"),
    re.compile(r"(?i)\binvoice\s*(?:no\.?|number|#)\s*[:#]?\s*([A-Za-z0-9._/\-]+)"),
    re.compile(r"(?i)\binv\.?\s*no\.?\s*[:#]?\s*([A-Za-z0-9._/\-]+)"),
]

def find_invoice_number(text: str, filename: Optional[str] = None) -> Optional[str]:
    txt = text or ""
    for rgx in RGX_INVOICE:
        m = rgx.search(txt)
        if m:
            candidate = m.group(1)
            # éviter une date au format 2025-10-06 prise comme numéro
            if not re.fullmatch(r"\d{4}[-/]\d{2}[-/]\d{2}", candidate):
                return candidate

    # Fallback sur le nom du fichier (ex: FACTURE_2024-123.pdf)
    if filename:
        stem = Path(filename).stem
        m = re.search(r"(?i)\b(?:facture|invoice|inv)[-_ ]*([A-Za-z0-9._/\-]+)", stem)
        if m:
            candidate = m.group(1)
            if not re.fullmatch(r"\d{4}[-/]\d{2}[-/]\d{2}", candidate):
                return candidate
        # dernier recours : motif alphanum usuel
        m = re.search(r"([A-Za-z0-9]{3,}[-_/][A-Za-z0-9._/\-]{2,})", stem)
        if m:
            return m.group(1)

    return None

# 2) Date
#   - "le 03/03/2025" (avec/sans "le")
#   - "03-03-2025"
#   - "2025-03-03"
RGX_DATE = re.compile(
    r"(?i)(?:\ble\s*)?(?P<d1>\d{2})[/-](?P<m1>\d{2})[/-](?P<y1>\d{4})\b"
    r"|(?P<y2>\d{4})-(?P<m2>\d{2})-(?P<d2>\d{2})\b"
)

def find_date(text: str) -> Optional[str]:
    m = RGX_DATE.search(text or "")
    if not m:
        return None
    if m.group("y1"):
        return f"{m.group('d1')}/{m.group('m1')}/{m.group('y1')}"
    return f"{m.group('d2')}/{m.group('m2')}/{m.group('y2')}"

# 3) Montants
#   a) Prioritaire : ligne "Total TTC*" (éventuellement "pour <mois> <année>")
RGX_TOTAL_TTC_STAR = re.compile(
    r"(?im)^\s*total\s*ttc\*\s*(?:pour\s+\S+(?:\s+\d{4})?)?\s*([€$]?)\s*([\d\s.,]+)\s*([€$]?)\s*$"
)

def find_amount_total_ttc_star(text: str) -> Optional[str]:
    m = RGX_TOTAL_TTC_STAR.search(text or "")
    if not m:
        return None
    cur_left, num, cur_right = m.group(1), m.group(2), m.group(3)
    cur = cur_left or cur_right or ""
    return f"{num.strip()}{cur}" if cur else num.strip()

#   b) Génériques : "Montant TTC", "Total TTC", "Total à payer", "Grand total", "Total", ...
RGX_AMOUNT_GENERIC = [
    re.compile(r"(?i)\b(?:total\s*(?:ttc|t\.t\.c\.)?|montant\s*ttc|total\s*à\s*payer|net\s*à\s*payer)\b[^0-9€$]*([€$]?)\s*([\d\s.,]+)\s*([€$]?)"),
    re.compile(r"(?i)\b(?:grand\s*total|amount\s*due|total)\b[^0-9€$]*([€$]?)\s*([\d\s.,]+)\s*([€$]?)"),
]

def find_amount_generic(text: str) -> Optional[str]:
    txt = text or ""
    for rgx in RGX_AMOUNT_GENERIC:
        m = rgx.search(txt)
        if m:
            cur_left, num, cur_right = m.group(1), m.group(2), m.group(3)
            cur = cur_left or cur_right or ""
            return f"{num.strip()}{cur}" if cur else num.strip()
    return None

# ============================
#   API PRINCIPALE
# ============================

def extract_invoice_data(pdf_path: str | Path) -> Dict[str, Any]:
    """
    Extrait (via regex uniquement) les infos principales d'une facture PDF :
      - 'facture'   : numéro de facture
      - 'date'      : dd/mm/yyyy
      - 'total_ttc' : ex. '255,63€' (priorité à la ligne 'Total TTC* ...')
      - 'fichier'   : nom du PDF
    """
    pdf_path = str(pdf_path)
    pdf_name = Path(pdf_path).name

    text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                text += page_text + "\n"
    except Exception as e:
        print(f"❌ Erreur lors de la lecture du PDF {pdf_path} : {e}")

    invoice_number = find_invoice_number(text, filename=pdf_path)
    date_str = find_date(text)
    total_ttc = find_amount_total_ttc_star(text) or find_amount_generic(text)

    return {
        "facture": invoice_number or "INCONNU",
        "date": date_str or "INCONNU",
        "total_ttc": total_ttc or "INCONNU",
        "fichier": pdf_name,
    }

# ============================
#   UTILITAIRE CHAÎNE SEULE
# ============================

def extract_invoice_number_from_string(s: str) -> Optional[str]:
    """Extrait un numéro de facture depuis une simple chaîne (regex uniquement)."""
    return find_invoice_number(s or "", filename=None)
