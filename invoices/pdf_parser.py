# invoices/pdf_parser.py
from __future__ import annotations

import re
import csv
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

from PyPDF2 import PdfReader

__all__ = [
    "extract_invoice_data",
    "extract_invoice_number_from_string",
    "find_invoice_number",
    "find_date",
    "process_input_folder_to_csv",
]

# ============================
#   REGEX UNIQUEMENT
# ============================

# 1) Numéro de facture
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

    # Fallback sur le nom de fichier
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


# 2) Date : "le 03/03/2025" | "03-03-2025" | "2025-03-03"
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


# 3) Montant TTC – priorité à "Total TTC* pour <Mois> <Année>"
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
    """
    Retourne (montant, source_motif, periode)
      - montant : ex '255,63€'
      - source_motif : 'TTC* mois' | 'TTC* générique' | 'montant générique' | 'non trouvé'
      - periode : ex 'Octobre 2025' si présente, sinon ''
    """
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
    txt = txt.replace("\u202f", " ")  # espace fine insécable
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
    """
    Extrait : facture (numéro), date (dd/mm/yyyy), total_ttc (string), période (si présente), fichier.
    """
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
        "periode": periode,              # ex. "Octobre 2025" si capté
        "source_montant": source,        # pour diagnostic (facultatif)
    }


# ============================
#   TRAITEMENT DOSSIER -> CSV
# ============================

def process_input_folder_to_csv(
    input_dir: str | Path = "./input",
    output_csv: str | Path = "./output/invoices_extract.csv",
) -> Path:
    """
    Parcourt ./input, extrait les infos pour chaque PDF, et écrit ./output/invoices_extract.csv.
    Colonnes : fichier, date_facture, numero_facture, total_ttc, periode
    """
    in_dir = Path(input_dir)
    out_csv = Path(output_csv)
    out_csv.parent.mkdir(parents=True, exist_ok=True)

    pdfs = sorted(in_dir.glob("*.pdf"))
    if not pdfs:
        print(f"⚠️ Aucun PDF trouvé dans {in_dir.resolve()}")
        # On crée quand même un CSV avec l'en-tête pour cohérence
        with out_csv.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["fichier", "date_facture", "numero_facture", "total_ttc", "periode"],
            )
            writer.writeheader()
        return out_csv

    rows: list[Dict[str, Any]] = []
    for pdf in pdfs:
        print(f"🔎 Extraction : {pdf.name}")
        data = extract_invoice_data(pdf)
        # Ne garder que les colonnes demandées
        rows.append({
            "fichier": data.get("fichier", pdf.name),
            "date_facture": data.get("date_facture", "INCONNU"),
            "numero_facture": data.get("numero_facture", "INCONNU"),
            "total_ttc": data.get("total_ttc", "INCONNU"),
            "periode": data.get("periode", ""),
        })

    with out_csv.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["fichier", "date_facture", "numero_facture", "total_ttc", "periode"],
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"✅ CSV généré : {out_csv.resolve()}")
    return out_csv


# ============================
#   UTILITAIRE CHAÎNE SEULE
# ============================

def extract_invoice_number_from_string(s: str) -> Optional[str]:
    """Extrait un numéro de facture depuis une simple chaîne (regex uniquement)."""
    return find_invoice_number(s or "", filename=None)


# ============================
#   MAIN (exécution directe)
# ============================

if __name__ == "__main__":
    # Lit ./input et écrit ./output/invoices_extract.csv
    process_input_folder_to_csv()
