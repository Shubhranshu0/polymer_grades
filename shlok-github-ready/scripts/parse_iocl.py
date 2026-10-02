#!/usr/bin/env python3
"""Parse IOCL All Polymer TDS PDF -> iocl.json
Layout: two-column text (desc left, applications right) + property tables.
"""
import pdfplumber, json, re

PDF = "/home/z/my-project/upload/IOCL All Polymer TDS.pdf"
OUT = "/home/z/my-project/extracted/iocl.json"

def clean(s):
    if s is None:
        return ""
    s = s.replace("\n", " ").replace("\u2013", "-").replace("\u2014", "-").replace("\u2019", "'")
    return re.sub(r"\s+", " ", s).strip()

grades = []
current = None

def flush():
    global current
    if current and current.get("grade"):
        grades.append(current)
    current = None

GRADE_RE = re.compile(
    r"\b(HDPE|LLDPE|LDPE|PP Homopolymer|PP Homo polymer|PP Random Copolymer|PP Impact Block Copolymer|PP Impact Copolymer|PP-ICP|PP Copolymer|PP)\s+"
    r"([A-Z]?[0-9]{3,4}[A-Z][A-Z0-9]{0,4}[A-Z]?)\s+is\b")

FAMILY_POLYMER_MAP = {
    "HDPE": "HDPE", "LLDPE": "LLDPE", "LDPE": "LDPE",
    "PP": "PP", "PP Homopolymer": "PP-Homo", "PP Homo polymer": "PP-Homo",
    "PP Random Copolymer": "PP-Random", "PP Impact Copolymer": "PP-Impact",
    "PP Impact Block Copolymer": "PP-Impact", "PP Copolymer": "PP-Impact",
    "PP-ICP": "PP-Impact",
}

# more robust: also catch "Homopolymer XXXXX is" from header family
FAM_BY_HEADER = {
    "High Density Polyethylene": "HDPE",
    "High Molecular Weight High Density Polyethylene": "HDPE",
    "Linear Low Density Polyethylene": "LLDPE",
    "Low Density Polyethylene": "LDPE",
    "Polypropylene Homopolymer": "PP-Homo",
    "Polypropylene Impact Copolymer": "PP-Impact",
    "Polypropylene Random Copolymer": "PP-Random",
    "Polypropylene": "PP",
}

with pdfplumber.open(PDF) as pdf:
    for pageno, page in enumerate(pdf.pages):
        text = page.extract_text() or ""
        lines = text.splitlines()
        if not lines:
            continue

        # Identify TDS start page: first line = "Family Application" and contains "Product Description:" (any case)
        if re.search(r"product\s+description\s*:", text, re.I):
            # Find grade
            gm = GRADE_RE.search(text)
            grade = None
            polymer_family = ""
            if gm:
                grade = gm.group(2)
                polymer_family = FAMILY_POLYMER_MAP.get(gm.group(1), gm.group(1))
            else:
                # fallback: family + code pattern from first line, e.g. "PP Homopolymer P1030FG is"
                fm = re.search(r"\b([A-Z][A-Za-z ]{3,40}?)\s+([A-Z]?[0-9]{3,4}[A-Z][A-Z0-9]{0,4}[A-Z]?)\s+is\b", text)
                if fm:
                    grade = fm.group(2)

            # First line: family + application (may be deeper on reprint pages)
            first = lines[0]
            fam_display = ""
            application = ""
            for fam in ["High Density Polyethylene", "High Molecular Weight High Density Polyethylene",
                        "Linear Low Density Polyethylene", "Polypropylene Impact Copolymer",
                        "Polypropylene Random Copolymer", "Polypropylene Homopolymer",
                        "Polypropylene", "Low Density Polyethylene"]:
                if first.startswith(fam):
                    fam_display = fam
                    application = first[len(fam):].strip()
                    break
            if not fam_display:
                # search first 20 lines (reprint pages have banner/disclaimer first)
                for ln in lines[:20]:
                    s = ln.strip()
                    for fam in ["High Molecular Weight High Density Polyethylene",
                                "High Density Polyethylene", "Linear Low Density Polyethylene",
                                "Polypropylene Impact Copolymer", "Polypropylene Random Copolymer",
                                "Polypropylene Homopolymer", "Polypropylene", "Low Density Polyethylene"]:
                        if s.startswith(fam):
                            fam_display = fam
                            application = s[len(fam):].strip()
                            break
                    if fam_display:
                        break
            # derive polymer from header if grade regex missed it
            if not polymer_family and fam_display:
                polymer_family = FAM_BY_HEADER.get(fam_display, fam_display)

            # Split columns by x-coordinate using the actual header positions
            words = page.extract_words()
            desc_hdr_x = 71.2
            apps_hdr_x = None
            typical_top = None
            for w in words:
                if w["text"].startswith("Recommended") and w["top"] < 150 and apps_hdr_x is None:
                    apps_hdr_x = w["x0"]
                if w["text"] == "Typical" and typical_top is None:
                    typical_top = w["top"]
                if w["text"].startswith("Product") and w["top"] < 150:
                    desc_hdr_x = w["x0"]
            if apps_hdr_x is None:
                apps_hdr_x = page.width / 2
            split_x = apps_hdr_x - 15
            BANNER_WORDS = {"teehsataD", "lacinhceT", "lanoisivorP"}

            def words_to_lines(ws):
                # group words into lines with 3pt top tolerance
                ws = sorted(ws, key=lambda w: w["top"])
                lines_out = []
                cur, cur_top = [], None
                for w in ws:
                    if cur_top is None or abs(w["top"] - cur_top) <= 3:
                        cur.append(w)
                        cur_top = w["top"] if cur_top is None else cur_top
                    else:
                        lines_out.append(" ".join(x["text"] for x in sorted(cur, key=lambda x: x["x0"])))
                        cur, cur_top = [w], w["top"]
                if cur:
                    lines_out.append(" ".join(x["text"] for x in sorted(cur, key=lambda x: x["x0"])))
                return lines_out

            # Left column: desc zone between headers and Typical Properties
            desc_top_limit = typical_top if typical_top else 300
            desc_words = [w for w in words if w["x0"] < split_x and 100 < w["top"] < desc_top_limit
                         and w["text"] not in BANNER_WORDS]
            desc_lines = words_to_lines(desc_words)
            desc_text = " ".join(clean(x) for x in desc_lines)
            desc_text = re.sub(r"Product Description:\s*", "", desc_text, flags=re.I)
            if grade == "1070FG":
                desc_text = desc_text.replace("P1070FG", "1070FG")
            dm = re.search(r"^(.*?)BIS Designation Code", desc_text)
            if dm:
                desc_text = dm.group(1)
            desc_text = clean(desc_text)

            # Right column: applications
            app_words = [w for w in words if w["x0"] >= split_x and w["top"] < (typical_top or 400)
                         and w["text"] not in BANNER_WORDS]
            app_text = " ".join(clean(x) for x in words_to_lines(app_words))
            app_text = re.sub(r"Recommended (Applications?|Application):\s*", "", app_text, flags=re.I)
            if grade == "1070FG":
                app_text = app_text.replace("P1070FG", "1070FG")
            # drop intro fragment: keep only text AFTER 'is recommended for ...:'
            im = re.search(r"is recommended for[^:]*:\s*(.*)$", app_text)
            if im:
                app_text = im.group(1)
            # cut trailing junk (footer bleed)
            app_text = re.split(r"Disclaimer|Registered Office|Contact Address", app_text)[0]
            apps = re.sub(r"\uf0b7 ?", "; ", app_text)
            apps_list = []
            for a in re.split(r";", apps):
                a = clean(a.strip(" ."))
                if a and len(a) > 2 and "is recommended" not in a.lower():
                    apps_list.append(a)
            if not apps_list and app_text:
                # keep first sentence as fallback
                apps_list = [clean(app_text)[:200]]

            # BIS code: from left-column words (avoids right-column interleave)
            bis_code = ""
            left_bis_words = [w for w in words if w["x0"] < split_x and w["top"] > 90
                              and w["text"] not in BANNER_WORDS]
            bis_lines = words_to_lines(left_bis_words)
            for bl in bis_lines:
                bm = re.search(r"BIS Designation Code.*?is:\s*([A-Z0-9:\-]+)", clean(bl))
                if not bm:
                    # two-line: 'as per IS 7328:2020 is:' + code
                    bm2 = re.search(r"is:\s*(IS\s?[0-9A-Z:\-]+)", clean(bl))
                    if bm2:
                        # code may be on next line
                        bis_code = clean(bm2.group(1))
                        break
                if bm:
                    bis_code = clean(bm.group(1).rstrip("."))
                    break
            if not bis_code:
                bism = re.search(r"BIS Designation Code[^:]*:\s*(IS\s?[0-9A-Z:\-]+)", clean(text))
                if bism:
                    bis_code = clean(bism.group(1).rstrip("."))
            # join split BIS codes like 'IS 7328-3B-BBQ-FXTA' possibly wrapped
            bis_code = re.sub(r"\s+", " ", bis_code)

            # Processing temp (normalize '2200C'/'220oC' artifacts -> '220°C')
            def norm_temp(t):
                t = clean(t)
                t = t.replace("–", "-").replace("\u00ba", "°")
                t = re.sub(r"o\s*C\b", "°C", t)
                t = re.sub(r"(\d+)0C\b", r"\1°C", t)
                t = re.sub(r"\s+°C", "°C", t)
                t = re.sub(r"\s*-\s*", " - ", t)
                return t.strip()
            ptm = re.search(r"Recommended Processing Temperature:\s*([\d\s\-–to0°C]+)", text)
            proc_temp = norm_temp(ptm.group(1)) if ptm else ""

            # Page-level grade override: p34 TDS carries MFI 8.0 which matches the
            # 1070FG row of the competition sheet (P1070FG on p61 has MFI 7).
            if pageno + 1 == 34 and grade and grade.upper().startswith("P1070FG"):
                grade = "1070FG"
            flush()
            current = {
                "company": "Indian Oil Corporation Ltd (IOCL)",
                "brand_family": "Propel",
                "polymer": polymer_family or fam_display,
                "polymer_display": fam_display,
                "application_segment": application,
                "grade": grade or f"UNKNOWN-{pageno+1}",
                "desc": [desc_text] if desc_text else [],
                "applications": apps_list,
                "bis_code": bis_code,
                "props": [],
                "processing": ([{"condition": "Recommended Processing Temperature", "window": proc_temp}] if proc_temp else []),
                "_pages": [pageno + 1],
            }
        elif current and "Recommended Processing Temperature" in text and not current["processing"]:
            ptm = re.search(r"Recommended Processing Temperature:\s*([\d\s\-–to0°C]+)", text)
            if ptm:
                t = clean(ptm.group(1))
                t = re.sub(r"(\d)0?C$", r"\1°C", t).replace("–", "-")
                current["processing"].append({"condition": "Recommended Processing Temperature", "window": t})

        # Parse property table on this page (for current grade)
        # PRIMARY: text-based extraction (values reliably inline)
        PROP_TEXT_RE = re.compile(
            r"^(.{8,70}?)\s+(ASTM\s?[A-Z]\s?[0-9]+[A-Z]?|ISO\s?[0-9\-]+|IS\s?[0-9]+)\s+"
            r"([A-Za-z/°%0-9\. ]{1,16}?)\s+([<>]?[\d\.]+.*|NB|No Break.*)$")
        in_props = False
        for ln in text.splitlines():
            s = re.sub(r"\s+", " ", ln).strip()
            if not in_props:
                if re.search(r"Typical Properties:", s):
                    in_props = True
                continue
            if re.match(r"^\*?Typical values", s) or "Recommended Processing Temperature" in s:
                in_props = False
                continue
            m = PROP_TEXT_RE.match(s)
            if m and "recommended" not in s.lower():
                name = clean(m.group(1))
                if re.match(r"^(Resin|Mechanical|Thermal|Environmental|Rheological|Optical)\s+Properties$", name):
                    continue
                current["props"].append({
                    "name": name, "test": clean(m.group(2)),
                    "unit": clean(m.group(3)), "value": clean(m.group(4)),
                })
        # SECONDARY: fill from table extraction if text missed some
        if len([p for p in current["props"] if p["value"]]) < 4:
            current["props"] = []  # restart with table-based
            for tbl in page.extract_tables():
                if not tbl:
                    continue
                rows = [[clean(str(c)) if c else "" for c in r] for r in tbl]
                hdr_idx = None
                for i, r in enumerate(rows[:5]):
                    if any("Tested Properties" in c for c in r if c):
                        hdr_idx = i
                        break
                if hdr_idx is None:
                    continue
                ncols = max(len(r) for r in rows[hdr_idx:])
                hdr = rows[hdr_idx] + [""] * (ncols - len(rows[hdr_idx]))
                name_col = test_col = unit_col = value_col = None
                for ci, c in enumerate(hdr):
                    if "Tested Properties" in c and name_col is None:
                        name_col = ci
                    elif "Test Method" in c and test_col is None:
                        test_col = ci
                    elif c.strip() == "UOM" and unit_col is None:
                        unit_col = ci
                    elif "Values" in c and value_col is None:
                        value_col = ci
                if value_col is None:
                    continue

                def cell_of(row, lo, hi):
                    return " ".join(c for c in row[lo:hi] if c).strip()

                last_test, last_unit = "", ""
                pending_name = ""
                for row in rows[hdr_idx + 1:]:
                    row = row + [""] * (ncols - len(row))
                    if not any(row):
                        continue
                    name = cell_of(row, 0, test_col if test_col else 1)
                    test = cell_of(row, test_col, unit_col) if test_col else ""
                    unit = cell_of(row, unit_col, value_col) if unit_col else ""
                    value = cell_of(row, value_col, None) if value_col is not None else ""
                    if name.startswith("Tested Properties"):
                        continue
                    if re.match(r"^(Resin|Mechanical|Thermal|Environmental|Rheological|Optical)\s+Properties$", name):
                        continue
                    if not name.strip():
                        if pending_name and (test or unit or value):
                            current["props"].append({
                                "name": pending_name, "test": test or last_test,
                                "unit": unit or last_unit, "value": value,
                            })
                            pending_name = ""
                            continue
                    if not test and not value and name:
                        pending_name = name
                        continue
                    if not test:
                        test = last_test
                    else:
                        last_test = test
                    if not unit:
                        unit = last_unit
                    else:
                        last_unit = unit
                    if pending_name and name:
                        name = pending_name + " " + name
                        pending_name = ""
                    if name and (value or test):
                        current["props"].append({
                            "name": name, "test": test, "unit": unit, "value": value,
                        })

flush()

# ---- Post-processing ----
# Clean artifacts from reversed banner text
for g in grades:
    for i, d in enumerate(g["desc"]):
        d = d.replace("teehsataD", "").replace("lacinhceT", "").replace("lanoisivorP", "")
        d = re.sub(r"\s+", " ", d).strip(" ;t")
        g["desc"][i] = clean(d)
    g["desc"] = [d for d in g["desc"] if d]

# NOTE: no P-prefix deduplication — the uploaded competition sheet lists
# P-series grades (P1030FG, P1030MG, ... P1200MAS) as separate entries and the
# TDS PDF carries separate datasheets for each, so every entry is kept.

# ---- Inject 3550MN (PDF page 28 text layer is font-corrupted; recovered via OCR) ----
grades.append({
    "company": "Indian Oil Corporation Ltd (IOCL)",
    "brand_family": "Propel",
    "polymer": "PP-Impact",
    "polymer_display": "Polypropylene Impact Copolymer",
    "application_segment": "Injection Molding & Compounding",
    "grade": "3550MN",
    "desc": ["PP Copolymer 3550MN is a heterophasic natural colored very high flow, medium impact "
             "resistance and nucleated grade produced by the latest Spheripol II Technology with "
             "following features: Excellent processability, Good balance of stiffness & Impact properties"],
    "applications": ["Appliances parts", "Thin wall & large products", "Automotive Compounds"],
    "bis_code": "IS 10910",
    "props": [
        {"name": "Melt Flow Index (230°C & 2.16 Kg)", "test": "ASTM D 1238", "unit": "gm/10 min", "value": "55.0"},
        {"name": "Density @ 23°C", "test": "ASTM D 1505", "unit": "gm/cm3", "value": "0.90"},
        {"name": "Tensile Strength @ Yield (60 mm/min)", "test": "ASTM D 638", "unit": "MPa", "value": "24"},
        {"name": "Elongation @ Yield (50 mm/min)", "test": "ASTM D 638", "unit": "%", "value": "5.0"},
        {"name": "Flexural Modulus (1.3 mm/min)", "test": "ASTM D 790", "unit": "MPa", "value": "1200"},
        {"name": "Notched Izod Impact Strength @ 23°C", "test": "ASTM D 256", "unit": "J/m", "value": "65"},
        {"name": "Heat Deflection Temperature (0.46 N/mm²)", "test": "ASTM D 648", "unit": "°C", "value": "105"},
        {"name": "Vicat Softening Point (10 N)", "test": "ASTM D 1525", "unit": "°C", "value": "145"},
    ],
    "processing": [{"condition": "Recommended Processing Temperature", "window": "170 - 230 °C"}],
    "_pages": [28],
    "_ocr": True,
})

# keep datasheet (page) order
grades.sort(key=lambda g: g["_pages"][0] if g.get("_pages") else 999)

with open(OUT, "w") as f:
    json.dump(grades, f, indent=1)

print(f"Parsed {len(grades)} IOCL grades")
from collections import Counter
print(Counter(g["polymer"] for g in grades))
unk = [g["grade"] for g in grades if g["grade"].startswith("UNKNOWN")]
print("Unknown grades:", unk)
no_props = [g["grade"] for g in grades if len(g["props"]) < 4]
print("Grades with <4 props:", no_props)
for g in grades:
    print(f"  {g['grade']:12s} {g['polymer']:14s} {g['application_segment'][:40]:40s} props={len(g['props'])}")
