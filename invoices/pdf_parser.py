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
]

# ============================
#   REGEX UNIQUEMENT
# ============================

# 1) Numéro de facture
#   - "Facture N°..."
#   - "Nº ...", "No ...", "N° ..."
#   - "Invoice No./Number/# ..."
RGX_INVOICE_PRIMARY = re.compile(r"(?i)\bfacture\s*(?:n[°ºo]\s*)?[:#]?\s*([A-Za-z0-9._/\-]+)")
RGX_INVOICE_FALLBACKS = [
    re.compile(r"(?i)\bn[°ºo]\s*[:#]?\s*([A-Za-z0-9._/\-]+)"),
    re.compile(r"(?i)\binvoice\s*(?:no\.?|number|#)\s*[:#]?\s*([A-Za-z0-9._/\-]+)"),
    re.compile(r"(?i)\binv\.?\s*no\.?\s*[:#]?\s*([A-Za-z0-9._/\-]+)"),
]

def _looks_like_date(s: str) -> bool:
    return bool(re.fullmatch(r"\d{4}[-/]\d{2}[-/]\d{2}", s))

def find_invoice_number(text: str, filename: Optional[str] = None) -> Optional[str]:
    txt = text or ""

    # Priorité "Facture N° ..."
    m = RGX_INVOICE_PRIMARY.search(txt)
    if m:
        cand = m.group(1).strip()
        if cand and not _looks_like_date(cand):
            return cand

    # Fallbacks
    for rgx in RGX_INVOICE_FALLBACKS:
        m = rgx.search(txt)
        if m:
            cand = m.group(1).strip()
            if cand and not _looks_like_date(cand):
                return cand

    # Fallback nom de fichier (ex: "... Facture ...pdf")
    if filename:
        stem = Path(filename).stem
        m = re.search(r"(?i)\b(?:facture|invoice|inv)[-_ ]*([A-Za-z0-9._/\-]+)", stem)
        if m:
            cand = m.group(1).strip()
            if cand and not _looks_like_date(cand):
                return cand

        m = re.search(r"([A-Za-z0-9]{3,}[-_/][A-Za-z0-9._/\-]{2,})", stem)
        if m:
            return m.group(1).strip()

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


# 3) Montant – “Total TTC* pour <Mois> <Année>”
#    Mois FR avec accents (un seul mot), année optionnelle, devise avant/après
RGX_TTC_MOIS = re.compile(
    r"(?im)^\s*total\s*ttc\*\s*"
    r"(?:pour\s+(?P<periode>[A-Za-zÀ-ÿ]+(?:\s+\d{4})?))?\s*"
    r"(?P<cur1>[€$]?)\s*(?P<amount>[\d\s.,]+)\s*(?P<cur2>[€$]?)\s*$"
)

# Fallback “TTC*” générique (sans exigence sur “pour <mois> <année>”)
RGX_TTC_STAR_GENERIC = re.compile(
    r"(?im)^\s*total\s*ttc\*\s*(?:pour\s+\S+(?:\s+\d{4})?)?\s*([€$]?)\s*([\d\s.,]+)\s*([€$]?)\s*$"
)

# Fallbacks plus génériques
RGX_AMOUNT_GENERIC = [
    re.compile(r"(?i)\b(?:total\s*(?:ttc|t\.t\.c\.)?|montant\s*ttc|total\s*à\s*payer|net\s*à\s*payer)\b[^0-9€$]*([€$]?)\s*([\d\s.,]+)\s*([€$]?)"),
    re.compile(r"(?i)\b(?:grand\s*total|amount\s*due|total)\b[^0-9€$]*([€$]?)\s*([\d\s.,]+)\s*([€$]?)"),
]

def _find_total_ttc(txt: str) -> tuple[Optional[str], str, str]:
    """
    Retourne (montant, source_motif, periode)
      - montant : ex '255,63€'
      - source_motif : 'TTC* mois' | 'TTC* générique' | 'montant générique' | 'non trouvé'
      - periode : ex 'Octobre 2025' si présente, sinon ''
    """
    # 1) Priorité: "Total TTC* pour <Mois> <Année> ..."
    m = RGX_TTC_MOIS.search(txt or "")
    if m:
        periode = (m.group("periode") or "").strip()
        cur = m.group("cur1") or m.group("cur2") or ""
        val = (m.group("amount") or "").strip()
        return (f"{val}{cur}" if cur else val, "TTC* mois", periode)

    # 2) “TTC*” générique
    m = RGX_TTC_STAR_GENERIC.search(txt or "")
    if m:
        cur = m.group(1) or m.group(3) or ""
        val = m.group(2).strip()
        return (f"{val}{cur}" if cur else val, "TTC* générique", "")

    # 3) Montants génériques
    for rgx in RGX_AMOUNT_GENERIC:
        m = rgx.search(txt or "")
        if m:
            cur = m.group(1) or m.group(3) or ""
            val = m.group(2).strip()
            return (f"{val}{cur}" if cur else val, "montant générique", "")

    return (None, "non trouvé", "")


# ============================
#   API PRINCIPALE
# ============================

def extract_invoice_data(pdf_path: str | Path) -> Dict[str, Any]:
    """
    Extrait (via regex uniquement) les infos principales d'une facture PDF :
      - 'facture'    : numéro de facture (après 'Facture N°')
      - 'date'       : dd/mm/yyyy
      - 'total_ttc'  : ex. '255,63€' (priorité 'Total TTC* pour <Mois> <Année>')
      - 'periode'    : ex. 'Octobre 2025' si détectée dans la ligne TTC*
      - 'fichier'    : nom du PDF
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
    total_ttc, source, periode = _find_total_ttc(text)

    return {
        "facture": invoice_number or "INCONNU",
        "date": date_str or "INCONNU",
        "total_ttc": total_ttc or "INCONNU",
        "periode": periode,
        "fichier": pdf_name,
        "source_montant": source,  # utile pour debug
    }


# ============================
#   UTILITAIRE CHAÎNE SEULE
# ============================

def extract_invoice_number_from_string(s: str) -> Optional[str]:
    """Extrait un numéro de facture depuis une simple chaîne (regex uniquement)."""
    return find_invoice_number(s or "", filename=None)
