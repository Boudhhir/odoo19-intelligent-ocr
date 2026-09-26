# -*- coding: utf-8 -*-
{
    "name": "Digiit Invoice OCR",
    "summary": "AI-powered vendor bill extraction (PDF / Image) via Groq + Tesseract",
    "description": """
Digiit Invoice OCR
==================
Upload a supplier invoice (PDF or image), extract its content with
Tesseract / pdfplumber, then call the Groq API (llama-3.3-70b-versatile)
to produce structured JSON, and finally create a draft vendor bill
(account.move) in Odoo 19 — with automatic creation of missing
partners, products and taxes.

All configuration values — INCLUDING the Groq API key — are hardcoded
in `digiit_invoice_ocr/config.py`. To change anything, edit that file
and restart Odoo. No Settings UI or environment variable is involved.
    """,
    "version": "19.0.1.0.0",
    "category": "Accounting/Accounting",
    "author": "Digiit",
    "website": "https://digiit.tn",
    "license": "LGPL-3",
    "depends": [
        "base",
        "account",
        "mail",
    ],
    "external_dependencies": {
        "python": [
            "requests",
            "pdfplumber",
            "pytesseract",
            "Pillow",
            "pdf2image",
            "pypdfium2",
        ],
    },
    "data": [
        "security/ir.model.access.csv",
        "views/account_move_views.xml",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
}
