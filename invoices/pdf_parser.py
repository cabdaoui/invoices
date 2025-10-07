# invoices/pdf_parser.py
from __future__ import annotations

import re
import csv
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

from PyPDF2 import PdfReader
from openpyxl import Workbook  # <-- NEW

__all__ = [
    "extract_invoice_data",
    "extract_invoice_number_from_string",
    "find_invoice_number",
    "find_date",
    "process_input_folder_to_csv",
    "process_input_folder_to_xlsx",  # <-- NEW
]

# ============================
#   REGEX UNIQUEMENT
# ============================

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

    m = RGX_INVOICE_PRIMARY.search(txt)
    if m:
        cand = m.group(1).strip()
        if cand and not _looks_like_date(cand):
            return cand

    for rgx in RGX_INVOICE_FALLBACKS:
        m = rgx.search(txt)
        if m:
            cand = m.group(1).strip()
            if cand and not _looks_like_date(cand):
                return cand

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

RGX_TTC_MOIS = re.compile(
    r"(?im)^\s*total\s*ttc\*\s*"
    r"(?:pour\s+(?P<periode>[A-Za-zÀ-ÿ]+(?:\s+\d{4})?))?\s*"
    r"(?P<cur1>[€$]?)\s*(?P<amount>[\d\s.,]+)\s*(?P<cur2>[€$]?)\s*$"
)

RGX_TTC_STAR_GENERIC = re.compile(
    r"(?im)^\s*total\s*ttc\*\s*(?:pour\s+\S+(?:\s+\d{4})?)?\s*([€$]?)\s*([\d\s.,]+)\s*([€$]?)\s*$"
)

RGX_AMOUNT_GENERIC = [
    re.compile(r"(?i)\b(?:total\s*(?:ttc|t\.t\.c\.)?|montant\s*ttc|total\s*à\s*payer|net\s*à\s*payer)\b[^0-9€$]*([€$]?)\s*([\d\s.,]+)\s*([€$]?)"),
    re.compile(r"(?i)\b(?:grand\s*total|amount\s*due|total)\b[^0-9€$]*([€$]?)\s*([\d\s.,]+)\s*([€$]?)"),
]

def _find_total_ttc(txt: str) -> Tuple[Optional[str], str, str]:
    m = RGX_TTC_MOIS.search(txt or "")
    if m:
        periode = (m.group("periode") or "").strip()
        cur = m.group("cur1") or m.group("cur2") or ""
        val = (m.group("amount") or "").strip()
        return (f"{val}{cur}" if cur else val, "TTC* mois", periode)

    m = RGX_TTC_STAR_GENERIC.search(txt or "")
    if m:
        cur = m.group(1) or m.group(3) or ""
        val = m.group(2).strip()
        return (f"{val}{cur}" if cur else val, "TTC* générique", "")

    for rgx in RGX_AMOUNT_GENERIC:
        m = rgx.search(txt or "")
        if m:
            cur = m.group(1) or m.group(3) or ""
            val = m.group(2).strip()
            return (f"{val}{cur}" if cur else val, "montant générique", "")

    return (None, "non trouvé", "")

# ============================
#   EXTRACTION TEXTE PyPDF2
# ============================

def _clean_text(txt: str) -> str:
    if not txt:
        return ""
    txt = txt.replace("\xa0", " ")
    txt = txt.replace("\u202f", " ")
    txt = txt.replace("€", " €")
    txt = re.sub(r"[ \t]+", " ", txt)
    txt = txt.replace("\r", "\n")
    return txt

def _extract_text_from_pdf(pdf_path: str | Path) -> str:
    parts: list[str] = []
    try:
        reader = PdfReader(str(pdf_path))
        for page in reader.pages:
            parts.append(page.extract_text() or "")
    except Exception as e:
        print(f"❌ Erreur lecture PDF '{pdf_path}': {e}")
    return _clean_text("\n".join(parts))

# ============================
#   API PRINCIPALE (1 PDF)
# ============================

def extract_invoice_data(pdf_path: str | Path) -> Dict[str, Any]:
    pdf_path = str(pdf_path)
    pdf_name = Path(pdf_path).name

    text = _extract_text_from_pdf(pdf_path)

    invoice_number = find_invoice_number(text, filename=pdf_path)
    date_str = find_date(text)
    total_ttc, source, periode = _find_total_ttc(text)

    return {
        "fichier": pdf_name,
        "date_facture": date_str or "INCONNU",
        "numero_facture": invoice_number or "INCONNU",
        "total_ttc": total_ttc or "INCONNU",
        "periode": periode,
        "source_montant": source,
    }

# ============================
#   TRAITEMENT DOSSIER -> CSV
# ============================

def process_input_folder_to_csv(
    input_dir: str | Path = "./input",
    output_csv: str | Path = "./output/invoices_extract.csv",
) -> Path:
    in_dir = Path(input_dir)
    out_csv = Path(output_csv)
    out_csv.parent.mkdir(parents=True, exist_ok=True)

    pdfs = sorted(in_dir.glob("*.pdf"))
    rows: list[Dict[str, Any]] = []

    for pdf in pdfs:
        print(f"🔎 Extraction : {pdf.name}")
        rows.append(extract_invoice_data(pdf))

    # écrit même vide (en-têtes)
    with out_csv.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["fichier", "date_facture", "numero_facture", "total_ttc", "periode"],
        )
        writer.writeheader()
        for r in rows:
            writer.writerow({
                "fichier": r.get("fichier", ""),
                "date_facture": r.get("date_facture", ""),
                "numero_facture": r.get("numero_facture", ""),
                "total_ttc": r.get("total_ttc", ""),
                "periode": r.get("periode", ""),
            })

    print(f"✅ CSV généré : {out_csv.resolve()}")
    return out_csv

# ============================
#   TRAITEMENT DOSSIER -> XLSX
# ============================

def process_input_folder_to_xlsx(
    input_dir: str | Path = "./input",
    output_xlsx: str | Path = "./output/invoices_extract.xlsx",
) -> Path:
    """
    Parcourt ./input, extrait les infos pour chaque PDF, et écrit ./output/invoices_extract.xlsx.
    Colonnes : fichier, date_facture, numero_facture, total_ttc, periode
    """
    in_dir = Path(input_dir)
    out_xlsx = Path(output_xlsx)
    out_xlsx.parent.mkdir(parents=True, exist_ok=True)

    pdfs = sorted(in_dir.glob("*.pdf"))
    rows: list[Dict[str, Any]] = []

    for pdf in pdfs:
        print(f"🔎 Extraction : {pdf.name}")
        rows.append(extract_invoice_data(pdf))

    wb = Workbook()
    ws = wb.active
    ws.title = "invoices"

    headers = ["fichier", "date_facture", "numero_facture", "total_ttc", "periode"]
    ws.append(headers)

    for r in rows:
        ws.append([
            r.get("fichier", ""),
            r.get("date_facture", ""),
            r.get("numero_facture", ""),
            r.get("total_ttc", ""),
            r.get("periode", ""),
        ])

    wb.save(out_xlsx)
    print(f"✅ XLSX généré : {out_xlsx.resolve()}")
    return out_xlsx

# ============================
#   UTILITAIRE CHAÎNE SEULE
# ============================

def extract_invoice_number_from_string(s: str) -> Optional[str]:
    return find_invoice_number(s or "", filename=None)

