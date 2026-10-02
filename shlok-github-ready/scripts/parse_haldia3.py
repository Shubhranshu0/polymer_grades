#!/usr/bin/env python3
"""Parse Haldia Polymer TDS PDF -> haldia.json (final version)."""
import pdfplumber, json, re

PDF = "/home/z/my-project/upload/Haldia Polymer merged.pdf"
OUT = "/home/z/my-project/extracted/haldia.json"

def clean(s):
    if s is None:
        return ""
    s = s.replace("\n", " ").replace("\u2013", "-").replace("\u2014", "-")
    return re.sub(r"\s+", " ", s).strip()

BRAND_MAP = {
    "Halene – H*": ("HDPE", "Halene H"),
    "Halene – L*": ("LLDPE", "Halene L"),
    "Halene – P*": ("PP", "Halene P"),
}

grades = []
current = None

def flush():
    global current
    if current and current.get("grade"):
        grades.append(current)
    current = None

def parse_text_props(text, current):
    """Fallback: parse property rows from raw text when table extraction has no grid."""
    section = "desc"
    last_test, last_unit = "", ""
    in_proc = False
    for ln in text.splitlines():
        s = clean(ln)
        if not s:
            continue
        if re.match(r"^Property\s+Test Method\s+Unit", s):
            section = "props"
            continue
        if section != "props":
            continue
        if re.match(r"^Suggested Processing", s):
            in_proc = True
            continue
        if in_proc:
            # format A: "Barrel Temperature 200 – 240 °C"
            mm = re.match(r"^([A-Za-z][A-Za-z /&]{3,40})\s+(\d+\s*/\s*\d+.*|\d+\s*-\s*\d+\s*°?C?|\d+\s*°C)$", s)
            if mm:
                current["processing"].append({"condition": mm.group(1), "window": mm.group(2)})
                continue
            # format B: "Barrel Temperature °C 180 - 235"
            mm = re.match(r"^([A-Za-z][A-Za-z /&]{3,40})\s+(°C|°)\s+([0-9].*)$", s)
            if mm:
                current["processing"].append({"condition": mm.group(1), "window": mm.group(3)})
            continue
        if re.match(r"^(Physical|Mechanical|Thermal|Optical) Propert", s, re.I):
            continue
        # name test unit value (units may contain spaces like 'g/10 min')
        mm = re.match(r"^(.{6,80}?)\s+((?:ASTM|ISO|IS|HPL)\s*[A-Z0-9 /\(\)\.,\-]+?)\s+([A-Za-z/°%0-9\. ]{2,12}?)\s+(-?[\d><=±\.]+.*)$", s)
        if mm:
            current["props"].append({
                "name": clean(mm.group(1)), "test": clean(mm.group(2)),
                "unit": clean(mm.group(3)), "value": clean(mm.group(4)),
            })
            continue
        mm = re.match(r"^(.{6,80}?)\s+((?:ASTM|ISO|IS|HPL)\s*[A-Z0-9 /\(\)\.,\-]+?)\s+(-?[\d><=±\.]+.*)$", s)
        if mm:
            current["props"].append({
                "name": clean(mm.group(1)), "test": clean(mm.group(2)),
                "unit": "", "value": clean(mm.group(3)),
            })
            continue

with pdfplumber.open(PDF) as pdf:
    for pageno, page in enumerate(pdf.pages):
        text = page.extract_text() or ""
        lines = text.splitlines()
        if not lines:
            continue
        brand_line = lines[0].strip()

        # Detect grade header (inline or separate-line styles)
        grade_name = None
        for i, ln in enumerate(lines[:6]):
            s = ln.strip()
            m1 = re.search(r"TECHNICAL DATA SHEET\s+(.+?)\s*$", s)
            if m1:
                grade_name = m1.group(1)
                break
            if s == "TECHNICAL DATA SHEET":
                # grade name on previous line
                for j in range(i - 1, -1, -1):
                    cand = lines[j].strip()
                    if re.match(r"^[A-Z0-9][A-Z0-9 ]{1,10}$", cand) and cand not in BRAND_MAP:
                        grade_name = cand
                        break
                break
        if grade_name and grade_name in BRAND_MAP:
            grade_name = None

        if grade_name:
            flush()
            polymer, family = BRAND_MAP.get(brand_line, ("", ""))
            current = {
                "company": "Haldia Petrochemicals Ltd (HPL)",
                "brand_family": family,
                "polymer": polymer,
                "grade": grade_name,
                "desc": [],
                "bis_code": "",
                "props": [],
                "processing": [],
                "_pages": [pageno + 1],
            }
            # description lines until property table
            for ln in lines[1:]:
                s = clean(ln)
                if not s:
                    continue
                if s.startswith("BIS Designation Code:"):
                    current["bis_code"] = clean(s.split(":", 1)[1])
                    break
                if re.match(r"^Property\s+Test Method", s) or s == "TECHNICAL DATA SHEET" or s in BRAND_MAP:
                    continue
                if s.startswith(grade_name) or s.startswith(("This grade", "This resin", "It is", "The ")):
                    current["desc"].append(s)
                elif current["desc"] and not s.startswith("*"):
                    current["desc"].append(s)

            # Parse tables
            found_table = False
            for tbl in page.extract_tables():
                if not tbl or len(tbl) < 2:
                    continue
                rows = [[clean(str(c)) if c else "" for c in r] for r in tbl]
                hdr = " ".join(x for x in rows[1] if x)
                if not ("Property" in hdr and ("Test Method" in hdr or "Unit" in hdr)):
                    continue
                found_table = True
                last_test, last_unit = "", ""
                in_proc = False
                for row in rows[2:]:
                    if not any(row):
                        continue
                    c0 = row[0]
                    if re.match(r"^Suggested Processing", c0):
                        in_proc = True
                        continue
                    if in_proc:
                        if len(row) >= 2 and row[1]:
                            current["processing"].append({"condition": c0, "window": row[1]})
                        elif len(row) >= 4 and row[3]:
                            current["processing"].append({"condition": c0, "window": row[3]})
                        continue
                    if re.match(r"^(Physical|Mechanical|Thermal|Optical|Other)\s+Propert", c0, re.I) and not any(row[1:]):
                        continue
                    if c0 == "Property" or c0.startswith("Property "):
                        continue
                    test = row[1] if len(row) > 1 else ""
                    unit = row[2] if len(row) > 2 else ""
                    value = row[3] if len(row) > 3 else ""
                    if test:
                        last_test = test
                    if unit:
                        last_unit = unit
                    current["props"].append({
                        "name": c0, "test": test or last_test,
                        "unit": unit or last_unit, "value": value,
                    })
            if not found_table:
                parse_text_props(text, current)
        elif current and "TECHNICAL DATA SHEET" not in text and any(
                re.match(r"^Suggested Processing Conditions", lines[i].strip()) for i in range(min(3, len(lines)))):
            # continuation page: processing conditions for previous grade
            for ln in lines[1:]:
                s = clean(ln)
                if not s or s in BRAND_MAP or s.startswith("*Halene"):
                    continue
                if re.match(r"^Suggested Processing", s) or s.startswith(("Mechanical Properties", "This grade meets")):
                    continue
                mm = re.match(r"^([A-Za-z][A-Za-z /&]{3,40})\s+([0-9].*)$", s)
                if mm:
                    current["processing"].append({"condition": mm.group(1), "window": mm.group(2)})
        elif current and "This grade meets the requirements" in text:
            pass  # compliance page for previous grade

flush()

with open(OUT, "w") as f:
    json.dump(grades, f, indent=1)

print(f"Parsed {len(grades)} Haldia grades")
from collections import Counter
print(Counter(g["polymer"] for g in grades))
no_props = [g["grade"] for g in grades if len(g["props"]) < 5]
print("Grades with <5 props:", no_props)
no_proc = [g["grade"] for g in grades if len(g["processing"]) == 0]
print("Grades with no processing:", no_proc)
