#!/usr/bin/env python3
"""Parse Haldia Polymer TDS (from pdftotext -layout output) into structured JSON."""
import json, re, sys

SRC = "/home/z/my-project/extracted/haldia.txt"
OUT = "/home/z/my-project/extracted/haldia.json"

def clean(s):
    if s is None:
        return ""
    s = s.replace("\u2013", "-").replace("\u2014", "-").replace("\u00b0", "°")
    return re.sub(r"\s+", " ", s).strip()

def main():
    with open(SRC) as f:
        raw_lines = f.read().splitlines()

    grades = []
    current = None
    section = None
    pending_prop = None  # property rows where unit/value wrap to next line

    PROP_TABLE_HEADERS = re.compile(r"^\s*Property\s+Test Method\s+Unit\s+Nominal Value", re.I)

    for ln in raw_lines:
        stripped = ln.strip()
        if not stripped:
            continue

        # New grade header
        m = re.search(r"TECHNICAL DATA SHEET\s+([A-Z0-9]+)\s*$", stripped)
        if m:
            if current:
                grades.append(current)
            current = {
                "company": "Haldia Petrochemicals Ltd (HPL)",
                "brand_family": None,
                "polymer": None,
                "grade": m.group(1),
                "desc": [],
                "bis_code": "",
                "props": [],
                "processing": [],
                "_start_page": None,
            }
            section = "desc"
            pending_prop = None
            continue

        if current is None:
            continue

        # Section transitions
        if re.search(r"Suggested Processing Conditions", stripped, re.I):
            section = "processing"
            pending_prop = None
            continue
        if PROP_TABLE_HEADERS.match(ln):
            section = "props"
            continue
        # End markers (footer / compliance page content)
        if re.match(r"^This grade meets the requirements", stripped):
            # finish current sheet content; compliance page follows
            if current:
                grades.append(current)
                current = None
                section = None
            continue
        if current is None:
            continue

        if section == "desc":
            if stripped.startswith("BIS Designation Code:"):
                current["bis_code"] = clean(stripped.split(":", 1)[1])
                section = "desc2"  # after BIS code, props table follows
                continue
            if "is the registered trademark" in stripped or "Mechanical Properties are on specimens" in stripped:
                continue
            # description lines (before BIS)
            if not current["bis_code"] and re.match(r"^[A-Z0-9]", stripped):
                current["desc"].append(clean(stripped))
        elif section == "desc2":
            # lines between BIS code and table header (usually blank)
            if PROP_TABLE_HEADERS.match(ln):
                section = "props"
            continue
        elif section == "props":
            if pending_prop is not None:
                # continuation line holding unit + value
                mm = re.match(r"^\s*([a-zA-Z/°%0-9²³\.]+)\s+(-?[\d><=±\.]+.*)$", ln)
                if mm:
                    current["props"].append({
                        "name": pending_prop["name"],
                        "test": pending_prop["test"],
                        "unit": clean(mm.group(1)),
                        "value": clean(mm.group(2)),
                    })
                    pending_prop = None
                    continue
                else:
                    # not a continuation; flush pending as-is
                    current["props"].append(pending_prop)
                    pending_prop = None
            if re.match(r"^\s*Physical Property\s*$", ln):
                continue
            if re.match(r"^\s*(Mechanical|Thermal|Optical|Other) Propert", ln, re.I):
                continue
            # main property row: name (test) unit value
            mm = re.match(r"^\s{0,10}([A-Z][A-Za-z0-9 ,\(\)/%°\.\-&\+]{6,90}?)\s{2,}((?:ASTM|ISO|IS)\s*[A-Z0-9 /\(\)\.,\-]+?)\s{2,}([A-Za-z/°%0-9²³\.]*)\s{2,}(-?[\d><=±\.]+.*)$", ln)
            if mm:
                current["props"].append({
                    "name": clean(mm.group(1)),
                    "test": clean(mm.group(2)),
                    "unit": clean(mm.group(3)),
                    "value": clean(mm.group(4)),
                })
                continue
            # property row where test method wrapped to next line
            mm = re.match(r"^\s{0,10}([A-Z][A-Za-z0-9 ,\(\)/%°\.\-&\+]{6,90}?)\s{4,}((?:ASTM|ISO|IS)\s*[A-Z0-9 /\(\)\.,\-]+)$", ln)
            if mm and not mm.group(2).endswith("min"):
                pending_prop = {"name": clean(mm.group(1)), "test": clean(mm.group(2)), "unit": "", "value": ""}
                continue
            # property name only, method+unit+value later
            mm = re.match(r"^\s{0,10}([A-Z][A-Za-z0-9 ,\(\)/%°\.\-&\+]{6,90}?)\s*$", ln)
            if mm and len(current["props"]) >= 0:
                pending_prop = {"name": clean(mm.group(1)), "test": "", "unit": "", "value": ""}
                continue
        elif section == "processing":
            mm = re.match(r"^\s*([A-Za-z ]{4,40}?)\s{2,}(-?\d+\s*[–-]\s*\d+\s*°?C?|-?\d+\s*°C)$", ln)
            if mm:
                current["processing"].append({
                    "condition": clean(mm.group(1)),
                    "window": clean(mm.group(2)),
                })
            elif re.match(r"^\*(Halene|HALENE)", stripped) or "Mechanical Properties are on specimens" in stripped:
                pass
        if stripped.startswith("* Halene"):
            continue

    if current:
        grades.append(current)

    # Deduplicate (each sheet appears once; compliance page was skipped)
    seen = {}
    for g in grades:
        seen[g["grade"]] = g
    grades = list(seen.values())

    # Classify polymer by grade pattern
    def classify(g):
        grade = g["grade"]
        first = grade[0].upper() if grade else ""
        # PP grades: start with P, 7, B2, M2, M3
        if grade.startswith("P5") or grade.startswith("P2") or grade.startswith("7") or grade.startswith("B2") or grade.startswith("M2") or grade.startswith("M3") or grade.startswith("R5"):
            return "PP"
        # LLDPE grades: F1, M1, R1, T1
        if grade.startswith(("F1", "M1", "R1", "T1")):
            return "LLDPE"
        return "HDPE"

    for g in grades:
        g["polymer"] = classify(g)
        g["brand_family"] = {"HDPE": "Halene H", "LLDPE": "Halene L", "PP": "Halene P"}[g["polymer"]]

    with open(OUT, "w") as f:
        json.dump(grades, f, indent=1)

    print(f"Parsed {len(grades)} Haldia grades")
    from collections import Counter
    print(Counter(g["polymer"] for g in grades))
    for g in grades[:5]:
        print(f"  {g['grade']}: {len(g['props'])} props, {len(g['processing'])} proc, BIS={g['bis_code']}")

if __name__ == "__main__":
    main()
