# invoices/pdf_parser.py
from __future__ import annotations

import re
from pathlib import Path
from typing import Optional, Dict, Any

import pdfplumber

# -------------------------------
# Helpers de normalisation texte
# -------------------------------

def _soft_normalize(text: str) -> str:
    """
    Normalise légèrement le texte issu d'un PDF/OCR :
    - remplace certains espaces insécables/typos
    - harmonise quelques tirets
    - compacte les espaces multiples
    """
    if not text:
        return ""
    t = text
    t = t.replace("\u00A0", " ").replace("\u2009", " ")
    t = t.replace("\u2011", "-").replace("\u2013", "-").replace("\u2014", "-")
    t = re.sub(r"[ \t]{2,}", " ", t)
    return t


def _normalize_invoice_number(raw: str) -> str:
    """
    Nettoie le numéro de facture capturé :
    - supprime décorations (#, :, ponctuation finale)
    - compactage espaces/tirets
    - corrections OCR prudentes (O->0, I/l->1) dans des tokens numériques
    - garde seulement caractères usuels
    """
    s = (raw or "").strip()
    s = re.sub(r"^[#:]*\s*", "", s)
    s = s.rstrip(".,;:")
    s = re.sub(r"[ \t]{2,}", " ", s)
    s = re.sub(r"-{2,}", "-", s)

    def _fix_token(tok: str) -> str:
        if len(tok) >= 3:
            tok = re.sub(r"(?<=\d)O(?=\d)", "0", tok)
            tok = re.sub(r"(?<=\d)[Il](?=\d)", "1", tok)
        return tok

    parts = re.split(r"([\-_/])", s)  # conserve séparateurs
    parts = [_fix_token(p) for p in parts]
    s = "".join(parts)
    s = re.sub(r"[^A-Za-z0-9\-_./ ]", "", s).strip()
    return s


# -------------------------------
# Regex précompilées
# -------------------------------

# Numéro de facture (variantes FR/EN)
_RGX_INVOICE = [
    # FR
    r"\b(?:facture|num[eé]ro\s+de\s+facture|r[eé]f[eé]rence\s+facture)\s*(?:n[°ºo])?\s*[:#]?\s*([A-Za-z0-9][A-Za-z0-9\-/_. ]{1,60})",
    r"\bn[°ºo]\s*[:#]?\s*([A-Za-z0-9][A-Za-z0-9\-/_. ]{1,60})",
    # EN
    r"\b(?:invoice\s*(?:no\.?|number|#)|inv\.?\s*no\.?)\s*[:#]?\s*([A-Za-z0-9][A-Za-z0-9\-/_. ]{1,60})",
    # Abrégé possible
    r"\bfact\s*[:#]?\s*([A-Za-z0-9][A-Za-z0-9\-/_. ]{1,60})",
]
_RGX_INVOICE = [re.compile(p, re.IGNORECASE) for p in _RGX_INVOICE]

# Dates courantes : dd/mm/yyyy, dd-mm-yyyy, yyyy-mm-dd (avec/sans "le ")
_RGX_DATE = re.compile(
    r"(?:\ble\s+)?(?P<d>\d{2})[/-](?P<m>\d{2})[/-](?P<y>\d{4})\b"
    r"|\b(?P<y2>\d{4})-(?P<m2>\d{2})-(?P<d2>\d{2})\b",
    re.IGNORECASE,
)

# Montants : "Total TTC", "Montant TTC", "Total à payer", "Grand total", "Total"
_RGX_AMOUNT = [
    r"\b(?:total\s*(?:ttc|t\.t\.c\.)?|montant\s*ttc|total\s*à\s*payer|net\s*à\s*payer)\b[^0-9€$]*([€$]?)\s*([\d\s.,]+)\s*([€$]?)",
    r"\b(?:grand\s*total|amount\s*due|total)\b[^0-9€$]*([€$]?)\s*([\d\s.,]+)\s*([€$]?)",
]
_RGX_AMOUNT = [re.compile(p, re.IGNORECASE) for p in _RGX_AMOUNT]


# -------------------------------
# Extraction de champs
# -------------------------------

def _extract_invoice_number(text: str, filename: Optional[str] = None) -> Optional[str]:
    t = _soft_normalize(text)
    for rgx in _RGX_INVOICE:
        m = rgx.search(t)
        if m:
            num = _normalize_invoice_number(m.group(1))
            # évite de prendre une date au format 2025-10-06
            if re.fullmatch(r"\d{4}[-/]\d{2}[-/]\d{2}", num):
                continue
            if len(num) >= 3:
                return num

    # Fallback depuis le nom de fichier (ex: FACTURE_2024-123.pdf)
    if filename:
        stem = _soft_normalize(Path(filename).stem)
        m = re.search(r"(?:facture|invoice|inv)[-_ ]*([A-Za-z0-9][A-Za-z0-9\-/_. ]{1,60})", stem, flags=re.IGNORECASE)
        if m:
            num = _normalize_invoice_number(m.group(1))
            if len(num) >= 3:
                return num
        # dernier recours : motif alphanum raisonnable
        m = re.search(r"([A-Za-z0-9]{3,}[-_/][A-Za-z0-9\-_/]{2,})", stem)
        if m:
            return _normalize_invoice_number(m.group(1))

    return None


def _extract_date(text: str) -> Optional[str]:
    t = _soft_normalize(text)
    m = _RGX_DATE.search(t)
    if not m:
        return None
    if m.group("y"):
        # dd/mm/yyyy ou dd-mm-yyyy -> formatte en dd/mm/yyyy
        d, mo, y = m.group("d"), m.group("m"), m.group("y")
        return f"{d}/{mo}/{y}"
    # yyyy-mm-dd -> formatte en dd/mm/yyyy
    y2, m2, d2 = m.group("y2"), m.group("m2"), m.group("d2")
    return f"{d2}/{m2}/{y2}"


def _format_amount_for_fr_display(num_str: str, currency_left: str, currency_right: str) -> str:
    """
    Convertit '2 345,67', '2,345.67', '2345.67' -> '2 345,67 €' (ou $).
    Si parsing impossible, renvoie la valeur nettoyée + devise si dispo.
    """
    s = (num_str or "").strip()
    s = s.replace(" ", "")

    # Détecter séparateur décimal probable
    dec = None
    if "," in s and "." in s:
        dec = "." if s.rfind(".") > s.rfind(",") else ","
    elif "," in s:
        dec = ","
    elif "." in s:
        dec = "."

    try:
        if dec == ",":
            s_clean = s.replace(".", "").replace(",", ".")
        elif dec == ".":
            s_clean = s.replace(",", "")
        else:
            s_clean = s  # entier

        val = float(s_clean)
        out = f"{val:,.2f}".replace(",", "X").replace(".", ",").replace("X", " ")
        cur = currency_left or currency_right or ""
        if cur:
            if cur == "€":
                return f"{out}€"
            return f"{cur}{out}" if cur == "$" else f"{out} {cur}"
        return out
    except Exception:
        cur = currency_left or currency_right or ""
        return f"{s}{cur}"


def _extract_amount(text: str) -> Optional[str]:
    t = _soft_normalize(text)
    for rgx in _RGX_AMOUNT:
        m = rgx.search(t)
        if m:
            cur_left, num_str, cur_right = m.group(1), m.group(2), m.group(3)
            return _format_amount_for_fr_display(num_str, cur_left, cur_right)
    return None


# -------------------------------
# API principale
# -------------------------------

def extract_invoice_data(pdf_path: str | Path) -> Dict[str, Any]:
    """
    Extrait les informations principales d'une facture PDF :
      - 'facture'  : numéro de facture (str) ou 'INCONNU'
