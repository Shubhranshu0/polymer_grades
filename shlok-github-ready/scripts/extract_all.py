#!/usr/bin/env python3
"""Extract text from all polymer TDS PDFs for analysis."""
import subprocess, os

files = {
    "haldia": "Haldia Polymer merged.pdf",
    "reliance": "Reliance Polymer merged.pdf",
    "iocl": "IOCL All Polymer TDS.pdf",
    "ongc": "ONGC POLYMER.pdf",
    "pe_price": "Polyethylene Price-September Price.pdf",
    "pp_price": "Polypropylene Price-September Month.pdf",
}

updir = "/home/z/my-project/upload"
outdir = "/home/z/my-project/extracted"
os.makedirs(outdir, exist_ok=True)

for name, fn in files.items():
    src = os.path.join(updir, fn)
    dst = os.path.join(outdir, f"{name}.txt")
    r = subprocess.run(["pdftotext", "-layout", src, dst],
                       capture_output=True, text=True)
    with open(dst) as f:
        content = f.read()
    print(f"{name}: {len(content)} chars, {len(content.splitlines())} lines")
