#!/usr/bin/env python3
"""Parse ONGC (OPaL) Polymer TDS PDF -> ongc.json"""
import pdfplumber, json, re

PDF = "/home/z/my-project/upload/ONGC POLYMER.pdf"
OUT = "/home/z/my-project/extracted/ongc.json"

def clean(s):
    if s is None:
        return ""
    s = s.replace("\n", " ").replace("\u2013", "-").replace("\u2014", "-").replace("\u2019", "'")
    return re.sub(r"\s+", " ", s).strip()

GRADE_RE = re.compile(r"\b(HDPE|LLDPE|PP Homo polymer|PP Homo Polymer|PP)\s+([A-Z][0-9A-Z]{3,6})\s+is\b")

FAM_HEADER = [
    "High Density Polyethylene", "Linear Low Density Polyethylene",
    "Polypropylene Homo Polymer", "Polypropylene",
]
FAM_MAP = {
    "High Density Polyethylene": "HDPE",
    "Linear Low Density Polyethylene": "LLDPE",
    "Polypropylene Homo Polymer": "PP-Homo",
    "Polypropylene": "PP-Homo",
}

grades = []
current = None

def flush():
    global current
    if current and current.get("grade"):
        grades.append(current)
    current = None

with pdfplumber.open(PDF) as pdf:
    for pageno, page in enumerate(pdf.pages):
        text = page.extract_text() or ""
        lines = text.splitlines()
        if not lines:
            continue

        if "Product Description:" in text or "Product Description :" in text:
            gm = GRADE_RE.search(text)
            grade = gm.group(2) if gm else None
            polymer_family = FAM_MAP.get(gm.group(1), "HDPE") if gm else ""

            # family + application from header line (search first 20 lines)
            fam_display, application = "", ""
            for ln in lines[:20]:
                s = ln.strip()
                for fam in FAM_HEADER:
                    if s.startswith(fam):
                        fam_display = fam
                        application = s[len(fam):].strip()
                        break
                if fam_display:
                    break
            # header family is authoritative for polymer type
            if fam_display:
                polymer_family = FAM_MAP.get(fam_display, polymer_family)
            if not polymer_family:
                polymer_family = FAM_MAP.get(gm.group(1), "HDPE") if gm else ""

            # two-column split
            words = page.extract_words()
            apps_hdr_x = None
            typical_top = None
            for w in words:
                if w["text"].startswith("Recommended") and w["top"] < 200 and apps_hdr_x is None:
                    apps_hdr_x = w["x0"]
                if w["text"] == "Typical" and typical_top is None:
                    typical_top = w["top"]
            split_x = (apps_hdr_x - 15) if apps_hdr_x else page.width / 2

            def words_to_lines(ws):
                ws = sorted(ws, key=lambda w: w["top"])
                out, cur, cur_top = [], [], None
                for w in ws:
                    if cur_top is None or abs(w["top"] - cur_top) <= 3:
                        cur.append(w)
                        cur_top = w["top"] if cur_top is None else cur_top
                    else:
                        out.append(" ".join(x["text"] for x in sorted(cur, key=lambda x: x["x0"])))
                        cur, cur_top = [w], w["top"]
                if cur:
                    out.append(" ".join(x["text"] for x in sorted(cur, key=lambda x: x["x0"])))
                return out

            desc_words = [w for w in words if w["x0"] < split_x and 100 < w["top"] < (typical_top or 400)]
            desc_text = " ".join(clean(x) for x in words_to_lines(desc_words))
            desc_text = re.sub(r"Product Description:?\s*", "", desc_text)
            desc_text = re.split(r"Recommended Processing Temperature|Regulatory Requirements", desc_text)[0]
            desc_text = clean(desc_text)

            app_words = [w for w in words if w["x0"] >= split_x and w["top"] < (typical_top or 400)]
            app_text = " ".join(clean(x) for x in words_to_lines(app_words))
            app_text = re.sub(r"(HDPE|LLDPE|PP [A-Za-z ]*)\s+[A-Z0-9]+\s+is recommended[^:]*:\s*", "", app_text)
            app_text = re.split(r"Note:|Disclaimer|Regulatory|Storage & Handling|Health and Safety", app_text)[0]
            apps_list = [clean(a.strip(" .")) for a in re.split(r"\s{2,}|;|,", app_text) if clean(a.strip(" .")) and len(clean(a.strip(" ."))) > 3]

            # processing temperature
            ptm = re.search(r"Recommended Processing Temperature:?\s*([\d\s\-–to0°C]+)", text)
            proc_temp = ""
            if ptm:
                t = clean(ptm.group(1))
                t = t.replace("–", "-")
                t = re.sub(r"(\d+)\s*0?C\b", r"\1°C", t)
                t = re.sub(r"\s*-\s*", " - ", t)
                proc_temp = clean(t)

            # BIS: not usually in ONGC TDS
            flush()
            current = {
                "company": "ONGC Petro Additions Ltd (OPaL)",
                "brand_family": "OPaL",
                "polymer": polymer_family,
                "polymer_display": fam_display,
                "application_segment": application,
                "grade": grade or f"UNKNOWN-{pageno+1}",
                "desc": [desc_text] if desc_text else [],
                "applications": apps_list,
                "bis_code": "",
                "props": [],
                "processing": ([{"condition": "Recommended Processing Temperature", "window": proc_temp}] if proc_temp else []),
                "_pages": [pageno + 1],
            }

        # parse property table (Sr. No / Properties / Test Method / Units / Values)
        if current:
            for tbl in page.extract_tables():
                if not tbl or len(tbl) < 2:
                    continue
                rows = [[clean(str(c)) if c is not None else "" for c in r] for r in tbl]
                hdr_idx = None
                for i, r in enumerate(rows[:5]):
                    if any("Properties" in c for c in r if c) and any("Test Method" in c for c in r if c):
                        hdr_idx = i
                        break
                if hdr_idx is None:
                    continue
                for row in rows[hdr_idx + 1:]:
                    cells = [c for c in row if c]
                    if not cells:
                        continue
                    # section headers
                    if re.match(r"^(Physical|Mechanical|Thermal|Optical|Other)\s+Properties$", cells[0]) and len(cells) == 1:
                        continue
                    if cells[0].startswith(("**", "*")):
                        continue
                    # drop leading sr no
                    if cells and cells[0].isdigit():
                        cells = cells[1:]
                    if not cells:
                        continue
                    # find test method cell
                    t_idx = None
                    for ci, c in enumerate(cells):
                        if re.match(r"^(ASTM|ISO)\s", c) or re.match(r"^IS\s?\d", c):
                            t_idx = ci
                            break
                    if t_idx is not None and t_idx > 0:
                        name = " ".join(cells[:t_idx])
                        test = cells[t_idx]
                        rest = cells[t_idx + 1:]
                        if len(rest) >= 2:
                            unit, value = rest[0], " ".join(rest[1:])
                        elif len(rest) == 1:
                            unit, value = "", rest[0]
                        else:
                            unit, value = "", ""
                        current["props"].append({"name": name, "test": test, "unit": unit, "value": value})
                    elif cells and len(cells) == 1 and current["props"]:
                        # wrapped name continuation -> prepend to last prop name? keep simple: skip
                        continue

flush()

with open(OUT, "w") as f:
    json.dump(grades, f, indent=1)

print(f"Parsed {len(grades)} ONGC grades")
from collections import Counter
print(Counter(g["polymer"] for g in grades))
no_props = [g["grade"] for g in grades if len(g["props"]) < 4]
print("Grades with <4 props:", no_props)
for g in grades:
    print(f"  {g['grade']:10s} {g['polymer']:10s} {g['application_segment'][:38]:38s} props={len(g['props'])} apps={len(g['applications'])}")
