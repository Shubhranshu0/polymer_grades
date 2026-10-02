#!/usr/bin/env python3
"""Parse Haldia Polymer TDS PDF using pdfplumber tables -> haldia.json"""
import pdfplumber, json, re

PDF = "/home/z/my-project/upload/Haldia Polymer merged.pdf"
OUT = "/home/z/my-project/extracted/haldia.json"

def clean(s):
    if s is None:
        return ""
    s = s.replace("\n", " ").replace("\u2013", "-").replace("\u2014", "-")
    return re.sub(r"\s+", " ", s).strip()

grades = []
current = None
last_fill = None  # last non-empty test-method/unit for continuation rows

def flush():
    global current
    if current and current.get("grade"):
        grades.append(current)
    current = None

with pdfplumber.open(PDF) as pdf:
    for pageno, page in enumerate(pdf.pages):
        text = page.extract_text() or ""
        first_line = text.splitlines()[0] if text else ""

        # Detect new grade sheet: "TECHNICAL DATA SHEET  {GRADE}"
        grade_match = None
        for ln in text.splitlines():
            m = re.search(r"TECHNICAL DATA SHEET\s+([A-Z0-9]+)\s*$", ln.strip())
            if m:
                grade_match = m
                break
        if grade_match:
            m = grade_match
            flush()
            current = {
                "company": "Haldia Petrochemicals Ltd (HPL)",
                "brand_family": "",
                "polymer": "",
                "grade": m.group(1),
                "desc": [],
                "bis_code": "",
                "props": [],
                "processing": [],
                "_pages": [pageno + 1],
            }
            # description lines: lines after header until 'Property' table or BIS
            for ln in text.splitlines()[1:]:
                s = clean(ln)
                if not s:
                    continue
                if s.startswith("BIS Designation Code:"):
                    current["bis_code"] = clean(s.split(":", 1)[1])
                    break
                if re.match(r"^Property\s+Test Method", s) or s.startswith("Property "):
                    break
                if current["grade"] and s.startswith(current["grade"]):
                    current["desc"].append(s)
                elif s.startswith(("This grade", "This resin", "It ", "The ")):
                    current["desc"].append(s)
                elif current["desc"]:
                    current["desc"].append(s)
        elif current and current["_pages"][-1] != pageno + 1 and "This grade meets the requirements" in text:
            current["_pages"].append(pageno + 1)

        # Parse tables on this page (only if we have an active current grade started on this page OR table continues)
        for tbl in page.extract_tables():
            rows = tbl
            if not rows:
                continue
            header = rows[1] if len(rows) > 1 else []
            hdr_str = " ".join(clean(str(c)) for c in header if c)
            is_prop_table = "Property" in hdr_str and ("Test Method" in hdr_str or "Unit" in hdr_str)
            if not is_prop_table:
                continue
            if current is None:
                continue
            last_test, last_unit = "", ""
            in_proc = False
            for row in rows[2:]:
                cells = [clean(str(c)) if c else "" for c in row]
                if not any(cells):
                    continue
                c0 = cells[0]
                if c0 == "Property":
                    continue
                if re.match(r"^Suggested Processing", c0):
                    in_proc = True
                    continue
                if in_proc:
                    if len(cells) >= 2 and cells[1]:
                        current["processing"].append({"condition": c0, "window": cells[1]})
                    elif len(cells) >= 4 and cells[3]:
                        # M5025L style: ['', unit, value] -> condition, °C, 180 - 235
                        current["processing"].append({"condition": c0, "window": cells[3]})
                    continue
                if re.match(r"^(Physical|Mechanical|Thermal|Optical|Other)\s+Propert", c0, re.I) and not any(cells[1:]):
                    continue
                # property row
                name = c0
                test = cells[1] if len(cells) > 1 else ""
                unit = cells[2] if len(cells) > 2 else ""
                value = cells[3] if len(cells) > 3 else ""
                if test:
                    last_test = test
                else:
                    test = last_test if not test else test
                if unit:
                    last_unit = unit
                current["props"].append({
                    "name": name,
                    "test": test,
                    "unit": unit or last_unit,
                    "value": value,
                })

flush()

# Post-process: classify polymer by brand marker in desc/first page text
def classify(g):
    grade = g["grade"]
    pp_prefixes = ("P", "7", "B2", "M2", "M3", "R5")
    lldpe_prefixes = ("F1", "M1", "R1", "T1")
    # Haldia structure: Halene H (HDPE): HD T9/T10/T10S/T6, M5xxx, M6xxx, B5500, B6401, E5201, E5201S, F5400
    if grade.startswith(("HD", "M5", "M6", "B5", "B6", "E5", "F5")):
        return "HDPE", "Halene H"
    if grade.startswith(("P", "7", "B2", "M2", "M3", "R5")):
        return "PP", "Halene P"
    if grade.startswith(("F1", "M1", "R1", "T1")):
        return "LLDPE", "Halene L"
    return "HDPE", "Halene H"

for g in grades:
    g["polymer"], g["brand_family"] = classify(g)

with open(OUT, "w") as f:
    json.dump(grades, f, indent=1)

print(f"Parsed {len(grades)} Haldia grades")
from collections import Counter
print(Counter(g["polymer"] for g in grades))
no_props = [g["grade"] for g in grades if len(g["props"]) < 5]
print("Grades with <5 props:", no_props)
no_proc = [g["grade"] for g in grades if len(g["processing"]) == 0]
print("Grades with no processing:", no_proc)
print("All grades:", [g["grade"] for g in grades])
