import re

# 1) Numéro de facture (gère: "Facture N°...", "Nº", "No", "Invoice No.", "INV No.")
RGX_INVOICE = [
    re.compile(r"(?i)\bfacture\s*(?:n[°ºo]\s*)?[:#]?\s*([A-Za-z0-9][A-Za-z0-9._/\-]{1,})"),
    re.compile(r"(?i)\bn[°ºo]\s*[:#]?\s*([A-Za-z0-9][A-Za-z0-9._/\-]{1,})"),
    re.compile(r"(?i)\binvoice\s*(?:no\.?|number|#)\s*[:#]?\s*([A-Za-z0-9][A-Za-z0-9._/\-]{1,})"),
    re.compile(r"(?i)\binv\.?\s*no\.?\s*[:#]?\s*([A-Za-z0-9][A-Za-z0-9._/\-]{1,})"),
]

def find_invoice_number(s: str) -> str | None:
    for rgx in RGX_INVOICE:
        m = rgx.search(s)
        if m:
            return m.group(1)
    return None

# 2) Date (capte: "le 03/03/2025", "03-03-2025", "2025-03-03")
RGX_DATE = re.compile(
    r"(?i)(?:\ble\s*)?(?P<d1>\d{2})[/-](?P<m1>\d{2})[/-](?P<y1>\d{4})\b"
    r"|(?P<y2>\d{4})-(?P<m2>\d{2})-(?P<d2>\d{2})\b"
)

def find_date(s: str) -> str | None:
    m = RGX_DATE.search(s)
    if not m:
        return None
    # Retourne simplement la sous-chaîne trouvée (sans normalisation hors-regex)
    return m.group(0)

# 3) Montant prioritaire "Total TTC*" (ligne entière, multi-lignes)
#    Exemples : "Total TTC* pour Mars 2025 323,00€" | "Total TTC*  $ 1,234.56"
RGX_TOTAL_TTC_STAR = re.compile(
    r"(?im)^\s*total\s*ttc\*\s*(?:pour\s+\S+(?:\s+\d{4})?)?\s*([€$]?)\s*([\d\s.,]+)\s*([€$]?)\s*$"
)

def find_amount_total_ttc_star(s: str) -> str | None:
    m = RGX_TOTAL_TTC_STAR.search(s)
    if not m:
        return None
    cur_left, num, cur_right = m.group(1), m.group(2), m.group(3)
    cur = cur_left or cur_right or ""
    return f"{num.strip()}{cur}" if cur else num.strip()

# 4) Montants génériques si la ligne "Total TTC*" n'existe pas
RGX_AMOUNT_GENERIC = [
    re.compile(r"(?i)\b(?:total\s*(?:ttc|t\.t\.c\.)?|montant\s*ttc|total\s*à\s*payer|net\s*à\s*payer)\b[^0-9€$]*([€$]?)\s*([\d\s.,]+)\s*([€$]?)"),
    re.compile(r"(?i)\b(?:grand\s*total|amount\s*due|total)\b[^0-9€$]*([€$]?)\s*([\d\s.,]+)\s*([€$]?)"),
]

def find_amount_generic(s: str) -> str | None:
    for rgx in RGX_AMOUNT_GENERIC:
        m = rgx.search(s)
        if m:
            cur_left, num, cur_right = m.group(1), m.group(2), m.group(3)
            cur = cur_left or cur_right or ""
            return f"{num.strip()}{cur}" if cur else num.strip()
    return None

# ------------------------------
# Démo rapide
# ------------------------------
if __name__ == "__main__":
    s_num = "Facture N°2025-03-621513456-000059041-IH-1"
    print("INVOICE:", find_invoice_number(s_num))  # -> 2025-03-621513456-000059041-IH-1

    s_date = "L'équipe Alan, le 03/03/2025"
    print("DATE:", find_date(s_date))              # -> le 03/03/2025 (ou 03/03/2025 selon le match)

    s_amt = "Total TTC* pour Mars 2025 323,00€\nAutre ligne"
    print("AMOUNT_TTC*:", find_amount_total_ttc_star(s_amt))  # -> 323,00€

    s_amt2 = "Montant TTC 1 234,56 €"
    print("AMOUNT_GENERIC:", find_amount_generic(s_amt2))     # -> 1 234,56 €
