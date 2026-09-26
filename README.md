# Intelligent OCR Module for Odoo 19

Academic final-year project (PFE) for automatic processing of supplier invoices and receipts in **Odoo 19 Community**.

## Overview

The module extracts information from native PDFs and scanned documents, structures the extracted data, and integrates it into Odoo vendor bills. It is designed to reduce manual data entry and improve accounting-data reliability.

## Main features

- Supplier invoice and receipt processing
- Native PDF text extraction with `pdfplumber`
- OCR for scanned documents with Tesseract
- Image preprocessing for OCR
- Structured extraction with Groq / Llama 3.3 70B
- French and Arabic document support
- Supplier and product matching / creation in Odoo
- Tunisian accounting rules, including fiscal stamp handling
- Fallback parsing when AI extraction is unavailable

## Technologies

- Python
- Odoo 19 Community
- PostgreSQL / Odoo ORM
- Tesseract OCR
- pdfplumber
- Pillow / OpenCV
- Groq API (Llama 3.3 70B)

## Project structure

```text
digiit_invoice_ocr/
├── models/
├── security/
├── services/
├── views/
├── __init__.py
├── __manifest__.py
└── config.py
```

## Security

No API keys or passwords are included in this repository. The Groq API key is read from the `GROQ_API_KEY` environment variable.

## Purpose

This repository is a portfolio version of an academic project. It demonstrates the design and implementation of an OCR/AI workflow integrated into Odoo 19.
