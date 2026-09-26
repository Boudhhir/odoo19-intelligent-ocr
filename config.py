# -*- coding: utf-8 -*-
"""
digiit_invoice_ocr — Module configuration
=========================================

Configuration values for the OCR module.

SECURITY: the Groq API key is intentionally NOT stored in this public
portfolio version. Set the GROQ_API_KEY environment variable locally.
"""

# ----------------------------------------------------------------------
# 1) Groq API
# ----------------------------------------------------------------------
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_TIMEOUT = 60                 # seconds
GROQ_TEMPERATURE = 0              # deterministic for accounting
GROQ_MAX_OCR_CHARS = 18000        # safety cap before sending to LLM

# ----------------------------------------------------------------------
# 2) Groq API KEY — loaded from an environment variable
#    Example (Windows PowerShell): $env:GROQ_API_KEY="your_key_here"
# ----------------------------------------------------------------------
import os

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")


def resolve_groq_api_key(env=None):
    """Return the Groq API key from the local environment."""
    return os.getenv("GROQ_API_KEY", GROQ_API_KEY)


# ----------------------------------------------------------------------
# 3) OCR
# ----------------------------------------------------------------------
# Languages loaded by Tesseract.
# IMPORTANT: only include languages you actually need. Loading extra
# languages (especially non-Latin ones like Arabic) makes Tesseract
# consider more candidate characters and noticeably degrades digit
# recognition on French/English invoices.
# Examples:
#   "fra+eng"       -> French + English (default, recommended)
#   "fra+eng+ara"   -> add Arabic if you actually receive Arabic invoices
TESSERACT_LANGS = "fra+eng"
PDF_OCR_DPI = 300                 # rasterization DPI for scanned PDFs
PDF_TEXT_MIN_CHARS = 20           # below this, fall back to OCR

# ----------------------------------------------------------------------
# 4) Business rules
# ----------------------------------------------------------------------
MIN_CONFIDENCE = 60               # below -> flagged for manual review
AUTO_CREATE_PARTNER = True
AUTO_CREATE_PRODUCT = True
AUTO_CREATE_TAX = True

# ----------------------------------------------------------------------
# 5) Defaults applied when creating new records
# ----------------------------------------------------------------------
DEFAULT_PRODUCT_TYPE = "consu"            # 'consu' or 'service'
DEFAULT_PRODUCT_PURCHASE_OK = True
DEFAULT_PRODUCT_SALE_OK = False
DEFAULT_PARTNER_SUPPLIER_RANK = 1
DEFAULT_PARTNER_IS_COMPANY = True
DEFAULT_TAX_NAME_TEMPLATE = "TVA %s%% (achats)"

# ----------------------------------------------------------------------
# 6) VAT prefix -> ISO country code
# ----------------------------------------------------------------------
COUNTRY_BY_VAT_PREFIX = {
    "TN": "TN", "FR": "FR", "MA": "MA", "DZ": "DZ",
    "BE": "BE", "DE": "DE", "ES": "ES", "IT": "IT",
    "PT": "PT", "NL": "NL", "LU": "LU", "GB": "GB",
}

# ----------------------------------------------------------------------
# 7) System prompt for Groq
# ----------------------------------------------------------------------
SYSTEM_PROMPT = (
    "You are an expert AI agent specialized in accounting data extraction, "
    "fully integrated with Odoo 19 ERP (account.move model). "
    "Your role is to transform raw OCR/PDF text from supplier invoices "
    "into clean, structured JSON ready for automatic vendor bill creation. "
    "You MUST output ONLY a valid JSON object — no prose, no markdown, "
    "no code fences, no explanations."
)

# ----------------------------------------------------------------------
# 8) USER prompt template — the placeholder {{OCR_TEXT_HERE}} is
#    replaced at runtime by the OCR text.
# ----------------------------------------------------------------------
USER_PROMPT_TEMPLATE = """\
==================================================
ODOO 19 INTEGRATION CONTEXT
==================================================
The extracted JSON will be consumed by an Odoo 19 automation that:

  1. Creates a vendor bill (account.move with move_type = 'in_invoice').
  2. Resolves the supplier:
     - Search res.partner by VAT, then email, then name (ilike).
     - If not found -> create new res.partner (supplier_rank = 1).
  3. Resolves each line's product:
     - Search product.product by default_code, then by name (ilike).
     - If not found -> create product.product (type='consu', purchase_ok=True).
  4. Resolves taxes:
     - Search account.tax by amount + type_tax_use='purchase'
       in the company's country.
     - If not found -> create account.tax (type_tax_use='purchase',
       amount_type='percent').
  5. Maps fields directly to Odoo 19:
       partner_id, invoice_date, invoice_date_due, ref, name,
       currency_id, invoice_line_ids (account.move.line),
       amount_untaxed, amount_tax, amount_total.

Odoo 19 specifics to respect:
  - Dates strictly in ISO format YYYY-MM-DD (Odoo Date field).
  - Currency as ISO 4217 code (EUR, USD, TND, MAD, ...).
  - VAT/TVA must keep its country prefix when present
    (e.g. "TN1234567A", "FR12345678901").
  - Numeric fields must be raw numbers (no spaces, no currency symbols,
    decimal separator = dot ".").
  - Tax rates as percentage numbers (e.g. 19, 7, 13, 20) -- never strings.

==================================================
INTELLIGENT PRE-PROCESSING
==================================================
Before extracting, internally clean and normalize the OCR text using
SEMANTIC understanding (do NOT rely on regex):

  * Fix common OCR confusions inside numeric tokens only:
      O -> 0, o -> 0, l -> 1, I -> 1, S -> 5, B -> 8
      (Never alter letters inside words/names.)
  * Normalize decimals: "1 234,56" or "1.234,56" -> 1234.56
  * Strip currency symbols from numeric values.
  * Reconnect words split across lines (hyphenation, line breaks).
  * Collapse repeated whitespace.
  * Identify the document's logical zones:
        HEADER  -> supplier identity and contact
        BODY    -> line items table
        FOOTER  -> totals (HT / TVA / TTC), payment terms, due date
  * Recognize multilingual labels (FR / EN / AR transliterated):
        "Total HT", "Montant HT", "Subtotal", "Net HT"
        "TVA", "VAT", "Taxe", "Tax"
        "Total TTC", "Net a payer", "Montant total", "Grand Total"
        "Date facture", "Invoice date", "Date d'emission"
        "Echeance", "Due date", "Date limite de paiement"
        "N Facture", "Facture N", "Invoice #", "Bill No."

==================================================
CRITICAL: TUNISIAN DINAR (TND / DT) — 3 DECIMAL PLACES
==================================================
The Tunisian Dinar uses THREE decimal places (millimes), NOT two like
the euro. This is the #1 source of misreading on Tunisian invoices.

Detection signals — assume TND/3-decimal format when ANY of these
are present:
  * Currency token: "DT", "TND", "DNT", "د.ت" (Arabic dinar)
  * Country: Tunisia / Tunisie / تونس
  * Tax labels: "TVA 19%", "TVA 13%", "TVA 7%" (Tunisian rates)
  * Tax ID: "MF" + alphanumeric like "1234567A/M/000"
  * Phone prefix: +216
  * "Timbre fiscal" mentioned

Number reading rules WHEN currency is TND/DT:
  ⚠️ THE COMMA IS ALWAYS THE DECIMAL SEPARATOR.
  ⚠️ THE SPACE IS ALWAYS THE THOUSANDS SEPARATOR.
  ⚠️ ANY 3 DIGITS AFTER THE COMMA ARE MILLIMES (decimal part).

  * "2 850,000 DT" -> 2850.0 (two thousand eight hundred fifty dinars,
                     zero millimes). The SPACE separates thousands; the
                     COMMA introduces the decimal millimes part. Do NOT
                     read this as 2.85 — that would lose three orders of
                     magnitude. The fact that "000" appears after the
                     comma does NOT make it negligible; it confirms TND
                     3-decimal format.
  * "480,500 DT"   -> 480.5 (four hundred eighty dinars, five hundred
                     millimes). NOT 0.4805. NOT 480500. There is no
                     space here, so no thousands group.
  * "8 550,000 DT" -> 8550.0 (eight thousand five hundred fifty dinars).
                     NOT 8.55. NOT 8.550.
  * "350,000 DT"   -> 350.0 (three hundred fifty dinars, zero millimes).
                     NOT 0.350. NOT 0.35.
  * "11 302,500 DT" -> 11302.5 (eleven thousand three hundred two
                     dinars, five hundred millimes). NOT 11.3025.
  * "18,500 DT"    -> 18.5 (eighteen dinars and five hundred millimes).
                     NOT 18500.
  * "1 800,000 DT" -> 1800.0 (the SPACE is the thousands separator).
  * "22,000 DT"    -> 22.0 (twenty-two dinars, zero millimes).
  * "0,450 DT"     -> 0.45 (four hundred fifty millimes).
  * "2 325,000 DT" -> 2325.0
  * "1 988,300 DT" -> 1988.3

Cross-check with the line arithmetic: q * unit_price ≈ line_total.
If you read "2 850,000 DT" as 2.85, the line total "8 550,000 DT" with
q=3 forces you to also misread it as 8.55 — and then the announced
subtotal "11 302,500 DT" cannot match sum(line_totals)=11.3 unless
you misread that too. ALL prices on a TND invoice follow the SAME
convention. Pick the convention that makes the line and footer math
balance, and apply it to every numeric token.

How to disambiguate "X,YYY" tokens:
  - 3 digits after comma + currency is DT/TND -> decimal separator
    (e.g. "18,500 DT" = 18.500)
  - 3 digits after comma + currency is EUR/USD -> thousands separator
    (e.g. "18,500 €" = 18500.00)
  - The footer totals always confirm: pick the interpretation that
    makes  sum(line_total) == subtotal  hold.

Quantities on Tunisian invoices use the SAME decimal convention.
"1 500" means one thousand five hundred (units), NOT 1.5. A space-
separated thousand is normal.

==================================================
CRITICAL: DECIMAL SEPARATOR RECOVERY
==================================================
OCR engines often LOSE thin glyphs like commas and decimal dots,
especially when the source image was binarized. This produces values
that look 100x larger than they really are. You MUST detect and
repair this.

Detection rule (apply per line and per total):
  Compute   q * unit_price ≈ line_total   for each line.
  Compute   sum(line_totals) ≈ subtotal   for the document.
  If the equality is off by exactly a factor of ~100 (or ~10, ~1000)
  on one term, the smaller-magnitude reading is almost certainly the
  correct one and the larger one had its decimal separator eaten by OCR.

Repair rule:
  When a price token has NO decimal separator and reinserting one two
  digits from the right makes the line arithmetic consistent, do it.
  Examples:
    OCR: qty=1, unit_price=10000, line_total=100.00
      -> unit_price was "100,00" with the comma lost. Use 100.00.
    OCR: qty=3, unit_price=5000, line_total=150.00
      -> 3 * 50.00 = 150.00. Use 50.00.
    OCR: qty=1, unit_price=20000, line_total=20000, but Total HT=450.00
         and other lines sum to 250.00
      -> this line is 200.00. Use 200.00 for both unit_price AND
         line_total.
    OCR: tax_rate=2000  -> 20.00 (i.e. 20%). Use 20.
    OCR: tax_total=9000, subtotal=450.00 -> 90.00 (TVA at 20%). Use 90.00.

==================================================
CRITICAL: MISSING / SWAPPED COLUMNS
==================================================
The OCR sometimes drops the "Quantité" column entirely or merges it
with the next column. Before emitting JSON, run these checks:

  * If unit_price is given AND line_total is given, but quantity is
    missing or = 1 and q*p does NOT equal t:
       -> recompute quantity = line_total / unit_price.
       -> Snap to a clean number when within 0.01 (e.g. 9.998 -> 10).
    Example: OCR shows "Bois de chauffage   stère   80,00 €   800,00 €"
    with no visible qty. -> quantity MUST be 10 (because 800/80=10),
    NOT 1.

  * If quantity * unit_price gives a value that is very different from
    line_total but swapping quantity and unit_price makes the math
    work, the OCR put them in the wrong columns. Swap them.
    Example: OCR shows qty=40, price=30, total=1200. 40*30=1200 so it
    looks fine — but if the description is "Main-d'oeuvre h." and the
    "h." indicates a unit, then quantity should be the hour count.
    When in doubt, prefer the assignment where unit_price is a typical
    "round" number (40, 50, 100, 250) over a quantity that looks like
    a unit price. Swap accordingly.

  * Anchor of truth: the footer totals (Total HT / TVA / Total TTC).
    Whatever you emit must satisfy:
        sum(line_total over lines)  ==  subtotal
        subtotal + tax              ==  total
    within 0.05. If not, revisit your line extraction.

==================================================
CRITICAL: FUEL STATION / RETAIL TICKETS — TTC LINE PRICES
==================================================
Some receipts (fuel stations, supermarkets, restaurants) print each
line amount as TTC (tax-inclusive), then show "Total HT" only in the
footer as a grand total — NOT as a per-line price.

RECOGNITION PATTERN:
  The text contains lines like:
    Carburant          75,82 EUR
    Cafe distributeur   1,20 EUR
    Total HT           64,18 EUR   <- this is the DOCUMENT TOTAL, not a line
    TVA 20%            12,84 EUR
    TOTAL TTC          77,02 EUR

  KEY: "Total HT" appears AFTER the last article line and BEFORE the
  tax line. It is a FOOTER AGGREGATE — not a product.
  The line prices (75,82 and 1,20) are TTC (they sum to 77,02 TTC).

RULE: when line_price_sum ≈ total_TTC (within 0.05), the lines are TTC.
  Convert each line individually: unit_price_HT = line_price_TTC / (1 + rate/100)
  NEVER use "Total HT" as the unit_price of any line.

CONCRETE EXAMPLE:
  Carburant          75,82 EUR  (TTC)
  Cafe distributeur   1,20 EUR  (TTC)
  Total HT           64,18 EUR  <- footer total, NOT a line price
  TVA 20%            12,84 EUR
  TOTAL TTC          77,02 EUR

  WRONG (common mistake):
    {"description":"Carburant",         "unit_price":64.18}  <- took "Total HT" as price
    {"description":"Cafe distributeur", "unit_price":1.00}
  CORRECT:
    {"description":"Carburant",         "unit_price":63.18, "tax_rate":20, "line_total":63.18}
    {"description":"Cafe distributeur", "unit_price":1.00,  "tax_rate":20, "line_total":1.00}
  amounts: {"subtotal":64.18, "tax":12.84, "total":77.02}

  Verification: 75.82/1.20=63.183≈63.18; 1.20/1.20=1.00; 63.18+1.00=64.18 ✓

  ALSO: "Sans Plomb 95 E10 / Volume: 42,38 L / Prix au litre: 1,789 EUR"
  are PRODUCT DETAIL lines — do NOT emit them as invoice line items.
  "CB SHELL ****0044" is the payment method — IGNORE.
  "TK475444318886" is the barcode — IGNORE.

==================================================
CRITICAL: TAX HANDLING
==================================================
  * If a line has NO visible tax column / tax label, tax_rate must be
    null (NOT 0, NOT a guessed default). The downstream system uses
    null to mean "no tax on this line" and will not apply any default
    tax.
  * If only the document footer shows a single tax (e.g. "TVA 20% on
    everything"), apply that rate to every line.
  * If different lines have different tax rates (mixed VAT), keep the
    per-line rate.
  * NEVER invent a tax rate just because the rest of the bill has one.

Sanity checks before emitting JSON:
  * 0 < tax_rate <= 30 in almost all real cases (VAT rates).
    A "tax_rate" of 2000 is wrong — divide by 100.
  * For each line: |q * unit_price * (1 - discount/100) - line_total|
    must be <= 0.05. If not, repair using the rule above.
  * |subtotal + tax - total| must be <= 0.05.
  * |sum(line_totals) - subtotal| must be <= 0.05.
  If after repair an equation still does not balance, set
  confidence_score lower and keep your best estimate.

==================================================
STRICT EXTRACTION RULES
==================================================
1. SUPPLIER (issuer of the invoice -- NOT the customer)
   - Take the entity in the header / letterhead.
   - Ignore blocks labeled "Client", "Facture a", "Bill to", "Customer".

2. DATES
   - Convert every date to YYYY-MM-DD.
   - If only DD/MM/YYYY is present, treat it as day/month/year.
   - If the year has 2 digits and is >= 50 -> 19xx, else -> 20xx.
   - If ambiguous or unreadable -> null.

3. AMOUNTS
   - subtotal = Total HT  (amount_untaxed)
   - tax      = TVA total (amount_tax)
   - total    = Total TTC (amount_total)
   - stamp_duty = "Timbre fiscal" / "TFL" / "Droit de timbre" / "Stamp"
                 → fixed-amount stamp duty (typically 1.000 DT in Tunisia
                 on services & some goods). It sits BETWEEN the VAT line
                 and the Total TTC. NEVER confuse it with a line item;
                 it is a tax-style adjustment, not a product.
                 If absent → null.
   - Sanity check: subtotal + tax + (stamp_duty or 0) == total
   - If only two of the three core amounts are present, leave the
     missing one null.

4. LINE ITEMS
   - Each row of the items table -> one entry in "lines".
   - quantity   -> MUST be an integer (no decimal part). Round to the
                   nearest whole number if the source shows a fractional
                   quantity. The downstream Odoo bill enforces integer
                   quantities; emitting 1.5 will be truncated to 1.
                   Default to 1 if absent.
   - discount   -> percentage (0-100); default 0 if absent.
   - unit_price -> unit price BEFORE tax (HT) when distinguishable.
   - tax_rate   -> per-line if shown; otherwise apply the global rate.
   - line_total -> quantity * unit_price * (1 - discount/100), HT.

5. CURRENCY
   - Detect from symbols/labels: euro->EUR, $->USD, "DT"/"TND"->TND,
     "MAD"/"DH"->MAD, GBP. Default to null if unclear.

6. VALIDATION and CONFIDENCE
   - If |total - (subtotal + tax)| > 0.05 -> lower confidence_score by 15.
   - If supplier name is missing -> lower by 20.
   - If invoice number is missing -> lower by 15.
   - If date is missing -> lower by 10.
   - If OCR text is visibly noisy/garbled -> lower by 10-20.
   - Final score must stay within 0-100.

7. ABSOLUTE PROHIBITIONS
   - NEVER invent values. Missing -> null.
   - NEVER use regex.
   - NEVER output anything other than the JSON object below.
   - NEVER wrap the JSON in code fences.
   - NEVER add comments inside the JSON.

==================================================
REQUIRED OUTPUT SCHEMA (Odoo 19 compatible)
==================================================
{
  "partner": {
    "name":    string | null,
    "street":  string | null,
    "city":    string | null,
    "zip":     string | null,
    "country": string | null,
    "phone":   string | null,
    "email":   string | null,
    "vat":     string | null
  },
  "invoice": {
    "number":   string | null,
    "date":     string | null,
    "due_date": string | null,
    "currency": string | null,
    "payment_reference": string | null
  },
  "amounts": {
    "subtotal":   number | null,
    "tax":        number | null,
    "stamp_duty": number | null,
    "total":      number | null
  },
  "lines": [
    {
      "description": string,
      "quantity":    integer | null,
      "unit_price":  number | null,
      "discount":    number | null,
      "tax_rate":    number | null,
      "line_total":  number | null
    }
  ],
  "confidence_score": number
}

==================================================
INPUT OCR TEXT
==================================================
{{OCR_TEXT_HERE}}

==================================================
OUTPUT
==================================================
Return ONLY the JSON object. Nothing before, nothing after.
"""

# ----------------------------------------------------------------------
# 9) USER prompt template — TICKET DE CAISSE (cash receipt)
#
#    A "ticket de caisse" (cash receipt / till receipt) is a simpler
#    document than an invoice:
#      * usually no supplier VAT number (no SIRET, no MF)
#      * sometimes no supplier address (just a brand name)
#      * very short product descriptions, often abbreviated
#      * quantities are small integers (1, 2, 3...)
#      * a single global VAT rate, often only shown in the footer
#      * no due_date, no payment_reference
#      * the "invoice number" is in fact a ticket number ("Ticket N°",
#        "Caisse 1 Ticket: 79776", "TK475...", etc.)
#
#    Output schema is kept IDENTICAL to the invoice prompt so the same
#    downstream Odoo code (_digiit_apply_ai_data) can consume it without
#    any branching.
# ----------------------------------------------------------------------
USER_PROMPT_TEMPLATE_TICKET = """\
==================================================
ODOO 19 INTEGRATION CONTEXT — CASH RECEIPT (TICKET DE CAISSE)
==================================================
The OCR text below comes from a CASH RECEIPT (ticket de caisse / till
receipt), NOT a full B2B invoice. It will still be consumed by the
SAME Odoo 19 automation that creates a vendor bill (account.move with
move_type = 'in_invoice'), so the output JSON schema is unchanged.

Key differences vs a full invoice — anticipate them:
  * The supplier is usually a retailer / restaurant / fuel station.
    The HEADER often has only a brand name and maybe an address.
  * Supplier VAT number (SIRET / MF / TVA intracommunautaire) is
    USUALLY ABSENT. Do NOT invent one. partner.vat -> null if absent.
  * There is NO "due date" on a cash receipt (it was paid on the spot).
    invoice.due_date -> null.
  * The "invoice number" field carries the TICKET number when present:
    "Ticket N°: 4", "Ticket: 79776", "TK475444318886", "N° 1234".
    If only a barcode-like token (TK...) is visible, use it.
  * Currency detection: DT/TND -> TND with 3 decimals,
    € -> EUR with 2 decimals, etc.
  * "Reçu" / "Espèce" / "CB" / "Cash" / "Carte" lines at the bottom
    indicate the payment method — IGNORE them, they are NOT line items.
  * "Total à payer", "TOTAL TICKET", "Net à payer" -> amount_total (TTC).
  * "HT" / "Total HT" -> subtotal.
  * "TVA xx%" amount -> tax.

==================================================
CRITICAL: MULTI-LINE ARTICLE NAMES (thermal receipts)
==================================================
Thermal till printers wrap long product names across 2 or more lines
because the paper is narrow (58 mm or 80 mm). The quantity and price
are ALWAYS on the LAST line of that article block — never before.

RULE: when you see a line that has NO numeric columns (no qty, no
price, no total) IMMEDIATELY BEFORE a line that DOES have numeric
columns, the two lines belong to the SAME article.  Concatenate them
with a space to form the full description.

Example from a real Tunisian receipt:

  OCR text:
    TWININGS ORANGE
    CANNELLE              1      3,950      3,950
    ORANGE                1      2,950      2,950

  WRONG extraction (splitting at every newline):
    { "description": "TWININGS ORANGE", ... }   <- price-less orphan
    { "description": "CANNELLE", qty: 1, unit_price: 3.950 }
    { "description": "ORANGE",   qty: 1, unit_price: 2.950 }

  CORRECT extraction (joining continuation lines):
    { "description": "TWININGS ORANGE CANNELLE", qty: 1, unit_price: 3.950 }
    { "description": "ORANGE",                   qty: 1, unit_price: 2.950 }

Apply this join rule BEFORE any other extraction step. A "price-less"
line is one that contains only text (letters, spaces, hyphens) with
NO digit sequences that could be a price or quantity.

==================================================
INTELLIGENT PRE-PROCESSING
==================================================
Same OCR-cleanup rules as for invoices:
  * Fix OCR confusions inside numeric tokens only (O->0, l->1, S->5…).
  * Normalize decimals: "1 234,56" or "1.234,56" -> 1234.56.
  * Strip currency symbols from numeric values.
  * Reconnect words split across lines.
  * Recognize multilingual labels (FR / EN / AR transliterated).

==================================================
CRITICAL: TUNISIAN DINAR (TND / DT) — 3 DECIMAL PLACES
==================================================
Tunisian receipts use THREE decimal places (millimes). All the rules
from the invoice prompt apply here verbatim:

  * "12,370 DT" -> 12.370 (twelve dinars and 370 millimes), NOT 12.37.
  * "1,490" on a Tunisian ticket -> 1.490 (one dinar 490 millimes).
  * Comma = decimal separator. Space = thousands separator.
  * Tunisian VAT rates: 7%, 13%, 19%.

If you see "TVA : 19%" with no other country markers, that ALONE is
a strong Tunisia signal. Combined with "DT", "TND", or +216 phone
prefix, treat the receipt as TND with 3 decimals.

CONCRETE EXAMPLE 1 — Tunisian retail ticket (TND, TVA 19%):
  Ticket N°: 4    11/09/2020 11:23
  FANTA ORANGE 50CL     1    1,490    1,490
  M.MAID ORANGE 33CL    1    1,000    1,000
  TWININGS ORANGE
  CANNELLE              1    3,950    3,950
  ORANGE                1    2,950    2,950
  JOKER JUS ORANGE      1    2,980    2,980
  HT  10,395   TTC  12,370
  TVA : 19%  1,975
  Total à payer : 12,370

  Expected JSON lines (unit_price = TTC / 1.19, rounded to 3 decimals):
  [
    {"description":"FANTA ORANGE 50CL",      "quantity":1,"unit_price":1.252,"tax_rate":19,"line_total":1.252},
    {"description":"M.MAID ORANGE 33CL",     "quantity":1,"unit_price":0.840,"tax_rate":19,"line_total":0.840},
    {"description":"TWININGS ORANGE CANNELLE","quantity":1,"unit_price":3.319,"tax_rate":19,"line_total":3.319},
    {"description":"ORANGE",                 "quantity":1,"unit_price":2.479,"tax_rate":19,"line_total":2.479},
    {"description":"JOKER JUS ORANGE",       "quantity":1,"unit_price":2.504,"tax_rate":19,"line_total":2.504}
  ]
  Expected amounts: {"subtotal":10.395,"tax":1.975,"total":12.370}

  IMPORTANT ROUNDING NOTE: sum(unit_price_HT * qty) may differ from
  printed "Total HT" by up to 0.01 per line due to millime rounding.
  Always use the PRINTED "Total HT" footer value as amounts.subtotal —
  do NOT recompute it from the lines. The per-line unit_price is
  independently rounded; small discrepancies are normal and expected.

CONCRETE EXAMPLE 2 — French fuel station ticket (EUR, TVA 20%):
  TOTAL ACCESS - A6
  Aire de Beaune - 21200   Station n 4421
  SIRET: 542 051 180 00477
  Date: 18/03/2026 08:34
  Carburant                75,82 EUR     <- TTC line price
  Cafe distributeur         1,20 EUR     <- TTC line price
  Total HT                 64,18 EUR     <- footer total HT (ALL lines combined)
  TVA 20%                  12,84 EUR
  TOTAL TTC                77,02 EUR
  TK475444318886

  KEY RULE: "Total HT 64,18 EUR" is the DOCUMENT FOOTER TOTAL, NOT the
  unit price of any line. The line prices (75,82 and 1,20) are TTC.
  Convert each line TTC -> HT individually:
    Carburant HT     = 75,82 / 1.20 = 63.183 -> round to 2 dec = 63.18
    Cafe distrib. HT =  1,20 / 1.20 =  1.000 -> round to 2 dec =  1.00
    Sum HT = 63.18 + 1.00 = 64.18  ✓ matches footer "Total HT 64,18"

  Expected JSON lines:
  [
    {"description":"Carburant",         "quantity":1,"unit_price":63.18,"tax_rate":20,"line_total":63.18},
    {"description":"Cafe distributeur", "quantity":1,"unit_price":1.00, "tax_rate":20,"line_total":1.00}
  ]
  Expected amounts: {"subtotal":64.18,"tax":12.84,"total":77.02}

  DO NOT emit "Sans Plomb 95 E10", "Volume: 42,38 L", "Prix au litre: 1,789 EUR"
  as line items — they are PRODUCT DETAIL lines, not invoice lines.
  DO NOT emit "CB SHELL ****0044" — it is the payment method.
  DO NOT emit "TK475444318886" — it is the barcode reference.

==================================================
CRITICAL: MISSING DECIMAL SEPARATORS
==================================================
Same arithmetic-anchor rule as for invoices. Compute
q * unit_price ≈ line_total per line; if a token is off by a factor
of 10/100/1000, reinsert the lost decimal separator. The footer
totals (subtotal / tax / total) are the anchor of truth.

==================================================
CRITICAL: TICKET PRICES ARE ALMOST ALWAYS TAX-INCLUSIVE (TTC)
==================================================
On a cash receipt / ticket de caisse, the price column shown to the
customer is the GROSS price (TTC, taxes included) — NOT the net price
(HT). This is a hard convention in retail (Tunisia, France, most of
the EU): the printed unit price already includes VAT. Examples:

  * "FANTA ORANGE 50CL  1  1,490  1,490"  on a Tunisian ticket with
    "TVA : 19%" in the footer →  1.490 is the TTC price, the HT price
    is  1.490 / 1.19 = 1.252.
  * "Café 1,20 EUR"  on a French ticket with "TVA 20%" in the footer
    →  1.20 is TTC, the HT price is  1.20 / 1.20 = 1.000.

The downstream Odoo bill expects unit_price in **HT** (it adds VAT on
top to compute TTC). If you emit the TTC price as unit_price and ALSO
set tax_rate, the bill total ends up inflated by the VAT amount.

RULE for ticket de caisse:
  1. Identify the global VAT rate from the footer
     ("TVA 19%", "TVA : 19%", "TVA 20%", etc.).
  2. For EACH line, convert the printed unit price and line total
     from TTC to HT:
        unit_price_HT = unit_price_TTC / (1 + tax_rate / 100)
        line_total_HT = line_total_TTC / (1 + tax_rate / 100)
  3. Keep tax_rate as the visible percentage (19, 20, 13, 7 …).
  4. Round each converted value to the currency's decimal precision:
        - TND / DT  -> 3 decimals (millimes)
        - EUR / USD / MAD -> 2 decimals
  5. Sanity-check: sum(line_total_HT) must equal the printed "Total HT"
     in the footer (within 0.05 in the currency unit). If it doesn't,
     adjust your conversion or your line extraction until it does.

ANCHOR (apply to every Tunisian-style ticket with HT + TVA + TTC
shown in the footer):
  * If the printed unit prices add up to the printed TTC total, they
    are TTC → CONVERT them as above.
  * If the printed unit prices add up to the printed HT total, they
    are already HT → keep them as-is.

For the "amounts" object (footer totals), emit the values AS PRINTED
on the ticket — DO NOT convert those:
   subtotal = printed "Total HT"
   tax      = printed "TVA xx%" amount
   total    = printed "Total TTC" / "Total à payer"

==================================================
STRICT EXTRACTION RULES
==================================================
1. SUPPLIER (the merchant)
   - Take the brand name at the top of the receipt
     (e.g. "INSOMNIA THE RESTAURANT", "TOTAL ACCESS - A6",
     "HOTEL LES TILLEULS").
   - Address may be a single line. Put it in partner.street.
   - VAT / SIRET / MF: extract ONLY if explicitly printed.
     If not visible -> null. NEVER fabricate.

2. DATES
   - Convert to YYYY-MM-DD. DD/MM/YYYY -> day/month/year.
   - If the receipt shows date AND time (e.g. "11/09/2020 11:23"),
     take only the date part.
   - No due_date on a cash receipt -> null.

3. AMOUNTS
   - subtotal     = "HT" / "Total HT" / "Sous-total HT"  -> amount_untaxed
   - tax          = "TVA xx%" amount line                -> amount_tax
   - total        = "Total à payer" / "TOTAL TICKET"
                    / "TOTAL TTC" / "Net à payer"        -> amount_total
   - stamp_duty   = "Timbre fiscal" / "TFL" / "Droit de timbre"
                    (Tunisian receipts) -> stamp_duty. Else null.
   - If only the TTC total is printed (no HT/TVA split — common on
     small French tickets), leave subtotal and tax null. The downstream
     bill will compute taxes from the per-line tax_rate.
   - Sanity check: subtotal + tax + (stamp_duty or 0) == total.

4. LINE ITEMS
   - Apply the MULTI-LINE ARTICLE join rule first (see above).
   - Each priced row of the items table -> one entry in "lines".
   - quantity:   integer; default 1 if absent.
   - discount:   percentage; default 0.
   - unit_price: unit price BEFORE tax (HT) — convert from TTC if needed.
   - tax_rate:   per-line if shown; otherwise the global footer rate.
   - line_total: quantity * unit_price (HT).

   DO NOT emit lines for:
     - "Total", "Sous-total", "HT", "TVA", "TTC", "Net à payer"
     - "Reçu", "Espèce", "CB", "Carte", "Rendu", "Monnaie"
     - "Caissier", "Client", "Table", "Caisse", "Ticket N°"
     - "Merci", "À bientôt", footer marketing text, Facebook URLs
     - Barcode reference tokens ("TK475…")

5. CURRENCY
   - Detect from symbols/labels: € -> EUR, $ -> USD,
     "DT" / "TND" / "DNT" -> TND, "MAD" / "DH" -> MAD.
   - If only digits are visible with no symbol, infer from country
     signals (e.g. Tunisian street name, "TVA 19%" -> TND).

6. VALIDATION and CONFIDENCE
   - Missing supplier name -> -20.
   - Missing ticket number  -> -10.
   - Missing date           -> -10.
   - |total - (subtotal + tax + stamp)| > 0.05 -> -15.
   - Noisy / garbled OCR    -> -10 to -20.
   - Final score must stay within 0-100.

7. ABSOLUTE PROHIBITIONS
   - NEVER invent values. Missing -> null.
   - NEVER use regex.
   - NEVER output anything other than the JSON object below.
   - NEVER wrap the JSON in code fences.
   - NEVER add comments inside the JSON.

==================================================
REQUIRED OUTPUT SCHEMA (identical to invoice schema)
==================================================
{
  "partner": {
    "name":    string | null,
    "street":  string | null,
    "city":    string | null,
    "zip":     string | null,
    "country": string | null,
    "phone":   string | null,
    "email":   string | null,
    "vat":     string | null
  },
  "invoice": {
    "number":   string | null,
    "date":     string | null,
    "due_date": string | null,
    "currency": string | null,
    "payment_reference": string | null
  },
  "amounts": {
    "subtotal":   number | null,
    "tax":        number | null,
    "stamp_duty": number | null,
    "total":      number | null
  },
  "lines": [
    {
      "description": string,
      "quantity":    integer | null,
      "unit_price":  number | null,
      "discount":    number | null,
      "tax_rate":    number | null,
      "line_total":  number | null
    }
  ],
  "confidence_score": number
}

==================================================
INPUT OCR TEXT
==================================================
{{OCR_TEXT_HERE}}

==================================================
OUTPUT
==================================================
Return ONLY the JSON object. Nothing before, nothing after.
"""
