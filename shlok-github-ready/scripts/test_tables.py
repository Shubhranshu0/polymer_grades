#!/usr/bin/env python3
"""Test pdfplumber table extraction on Haldia PDF pages."""
import pdfplumber

PDF = "/home/z/my-project/upload/Haldia Polymer merged.pdf"

with pdfplumber.open(PDF) as pdf:
    # Test page 1 (HD T9 props table) and page for M5025L
    for pageno in [0, 1]:
        page = pdf.pages[pageno]
        tables = page.extract_tables()
        print(f"=== Page {pageno+1}: {len(tables)} tables ===")
        for t in tables:
            for row in t[:20]:
                print([str(c)[:35] if c else "" for c in row])
            print("---")
