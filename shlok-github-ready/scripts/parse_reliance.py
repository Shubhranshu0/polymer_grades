#!/usr/bin/env python3
"""Parse Reliance Polymer TDS PDF (Relene PE + Repol PP) -> reliance.json"""
import pdfplumber, json, re

PDF = "/home/z/my-project/upload/Reliance Polymer merged.pdf"
OUT = "/home/z/my-project/extracted/reliance.json"

def clean(s):
    if s is None:
        return ""
    s = s.replace("\n", " ").replace("\u2013", "-").replace("\u2014", "-").replace("\u2019", "'").replace("\u201c", '"').replace("\u201d", '"')
    return re.sub(r"\s+", " ", s).strip()

# text-based property row: name test unit value
PROP_RE = re.compile(
    r"^(.{5,75}?)\s+(ASTM\s?[A-Z]\s?[0-9]+[A-Z]?|ISO\s?[0-9\-]+|IS\s?[0-9: \-]+?)\s+"
    r"([A-Za-z/°%0-9²³\.\u00b2 ]{1,14}?)\s+([<>]?[\d\.]+.*|NB|No Break|Not.break.*|Nil.*)$")

grades = []
current = None

def flush():
    global current
    if current and current.get("grade"):
        grades.append(current)
    current = None

def classify_polymer(brand, header_text, grade):
    h = header_text.upper()
    if brand in ("Repol", "Relpure") or "COPOLYMER" in h and "POLYPROPYLENE" in h:
        if "RANDOM COPOLYMER" in h or "RANDOM" in h:
            return "PP-Random"
        if "IMPACT COPOLYMER" in h or "IMPACT" in h:
            return "PP-Impact"
        if "HOMOPOLYMER" in h or "HOMO" in h or brand == "Repol":
            return "PP-Homo"
        return "PP-Homo"
    # Relene / Relpure
    if "LINEAR LOW" in h:
        return "LLDPE"
    if "LOW DENSITY" in h:
        return "LDPE"
    return "HDPE"

with pdfplumber.open(PDF) as pdf:
    for pageno, page in enumerate(pdf.pages):
        text = page.extract_text() or ""
        lines = text.splitlines()
        if not lines:
            continue

        # Detect TDS start: brand + grade + is
        gm = re.search(r"\b(Relene|Relpure|Repol)\s+([A-Z0-9]+(?:UV)?)\s*(\([^)]*\))?\s*,?\s+is\b", text)
        if gm and "Note:" not in lines[0]:
            brand = gm.group(1)
            grade = gm.group(2)

            # header info from first 3 lines (family + application)
            hdr = " ".join(clean(l) for l in lines[:4])
            # application subtitle: "FOR XXX" lines
            app_m = re.search(r"FOR\s+([A-Z][A-Z &,()\-]{4,70})", hdr)
            application = app_m.group(1).strip() if app_m else ""
            # family display
            fam_display = ""
            for fam in ["HIGH DENSITY POLYETHYLENE", "LINEAR LOW DENSITY POLYETHYLENE",
                        "LOW DENSITY POLYETHYLENE", "HIGH MOLECULAR WEIGHT HIGH DENSITY POLYETHYLENE",
                        "IMPACT COPOLYMER", "RANDOM COPOLYMER", "HOMOPOLYMER", "POLYETHYLENE RESIN"]:
                if fam in hdr.upper():
                    fam_display = fam
                    break
            # cleaner application text from "FOR ..." subtitle
            for l in lines[:4]:
                if re.match(r"^FOR\s+", l.strip()):
                    application = clean(l.strip())[4:].strip()
                    break

            # description: from brand line until BIS or Typical Characteristics
            desc_parts = []
            in_desc = False
            bis_code = ""
            for l in lines:
                s = clean(l)
                if re.search(rf"\b{brand}\s+{re.escape(grade)}\b", s) and not in_desc:
                    in_desc = True
                if in_desc:
                    if s.startswith("BIS Designation Code"):
                        bis_code = clean(s.split(":", 1)[1])
                        in_desc = False
                        break
                    if s.startswith("Typical Characteristics"):
                        in_desc = False
                        break
                    # skip header lines already consumed
                    if s == clean(lines[0]) or (len(lines) > 1 and s == clean(lines[1])) or (len(lines) > 2 and s == clean(lines[2])):
                        continue
                    desc_parts.append(s)

            # applications section
            apps = []
            in_apps = False
            props = []
            in_props = False
            processing = []
            in_proc = False
            pending_name = None
            pending_unit = ""
            for l in lines:
                s = clean(l)
                if not s:
                    continue
                if s.startswith("Typical Characteristics"):
                    in_props = True
                    in_apps = False
                    in_proc = False
                    continue
                if s.startswith(("Typical Processing Conditions", "Typical Processing Temperature", "Typical Process Temperature")):
                    in_proc = True
                    in_props = False
                    in_apps = False
                    mt = re.search(r"Typical Process(?:ing)? (?:Conditions|Temperature):?\s*(.+)$", s)
                    if mt and re.search(r"\d", mt.group(1)):
                        processing.append({"condition": "Typical Processing Temperature", "window": clean(mt.group(1))})
                    continue
                if s == "Applications" or s.startswith("Applications "):
                    in_apps = True
                    in_proc = False
                    in_props = False
                    continue
                if s.startswith(("Regulatory Information", "Storage Recommendations", "DISCLAIMER", "Disclaimer")):
                    in_apps = False
                    in_proc = False
                    in_props = False
                    continue

                if in_props:
                    if s.startswith(("* Typical", "*Typical", "Note:", "Note :", "Note")):
                        in_props = False
                        continue
                    # hydrostatic pressure test header + sub-rows
                    if re.match(r"^Hydrostatic Pressure Test", s):
                        props.append({"name": "Hydrostatic Pressure Test", "test": "ISO 1167", "unit": "Hrs", "value": ""})
                        continue
                    m_h = re.match(r"^([\d\.]+\s*MPa\s*@\s*-?\d+\s*°?C?)\s+([<>]?[\d\.]+)\s*$", s)
                    if m_h and props and props[-1]["name"] == "Hydrostatic Pressure Test":
                        props[-1]["value"] += ("; " if props[-1]["value"] else "") + f"{clean(m_h.group(1))}: {clean(m_h.group(2))}"
                        continue
                    m = PROP_RE.match(s)
                    if m:
                        name, test, unit, value = (clean(m.group(i)) for i in range(1, 5))
                        props.append({"name": name, "test": test, "unit": unit, "value": value})
                        continue
                    # row with only name + unit/value (test wrapped) or value-only continuation
                    m2 = re.match(r"^(.{5,75}?)\s+([A-Za-z/°%0-9²³\. ]{1,14}?)\s+([<>]?[\d\.]+.*)$", s)
                    if m2 and not re.match(r"^\s*•", s):
                        # name unit value without test -> use previous test
                        prev_test = props[-1]["test"] if props else ""
                        props.append({"name": clean(m2.group(1)), "test": prev_test,
                                      "unit": clean(m2.group(2)), "value": clean(m2.group(3))})
                        continue
                    m3 = re.match(r"^([<>]?[\d\.]+.*)$", s)
                    if m3 and props:
                        # continuation value line (e.g. sub-rows of hydrostatic test)
                        props[-1]["value"] += " / " + clean(m3.group(1))
                        continue
                    # name only (wrap)
                    if re.match(r"^[A-Za-z]", s) and len(s) > 5 and not s.startswith("Note"):
                        pending_name = s
                        continue
                elif in_proc:
                    m = re.match(r"^(Melt temperature|Mold temperature|Melt Temperature|Mould Temperature|Processing temperatures?)(.*)$", s, re.I)
                    if m:
                        processing.append({"condition": "Processing Temperature" if m.group(1).lower().startswith("processing") else clean(m.group(1)), "window": clean(m.group(2)).lstrip(": ")})
                    elif re.match(r"^Note:", s):
                        in_proc = False
                elif in_apps:
                    if s.startswith(("•", "-", "\u2022")):
                        apps.append(clean(s.lstrip("•- ")))
                    elif apps and not s.startswith(("Note", "Note:", "Reliance Industries", "Updated as of", "*")):
                        # wrapped continuation
                        apps[-1] += " " + s
                    elif not apps and len(s) > 3 and not s.startswith(("Note", "Reliance Industries")):
                        apps.append(s)

            flush()
            current = {
                "company": "Reliance Industries Ltd (RIL)",
                "brand_family": brand,
                "polymer": classify_polymer(brand, hdr + " " + fam_display, grade),
                "polymer_display": fam_display.title() if fam_display else brand,
                "application_segment": application.title() if application else "",
                "grade": grade,
                "desc": desc_parts,
                "applications": [a for a in apps if a],
                "bis_code": bis_code,
                "props": props,
                "processing": processing,
                "_pages": [pageno + 1],
            }
        elif current:
            # continuation page: parse props continuation + processing conditions & applications
            in_apps = False
            in_proc = False
            in_props = not re.match(r"^(Regulatory Information|Storage Recommendations|DISCLAIMER)", lines[0].strip()) and not current["processing"]
            for l in lines:
                s = clean(l)
                if not s:
                    continue
                if s.startswith(("* Typical", "*Typical", "Note:")):
                    in_props = False
                    continue
                if s.startswith(("Typical Processing Conditions", "Typical Processing Temperature", "Typical Process Temperature")):
                    in_proc = True
                    in_apps = False
                    # line may itself carry the temperature
                    mt = re.search(r"Typical Process(?:ing)? (?:Conditions|Temperature):?\s*(.+)$", s)
                    if mt and re.search(r"\d", mt.group(1)):
                        current["processing"].append({"condition": "Typical Processing Temperature", "window": clean(mt.group(1))})
                    continue
                if s == "Applications" or s.startswith("Applications ") or s.startswith("Product description & applications"):
                    in_apps = True
                    in_proc = False
                    in_props = False
                    continue
                if s.startswith(("Regulatory Information", "Storage Recommendations", "DISCLAIMER", "Disclaimer", "Note:")):
                    in_apps = False
                    in_proc = False
                    in_props = False
                    continue
                if in_props:
                    m = PROP_RE.match(s)
                    if m:
                        name, test, unit, value = (clean(m.group(i)) for i in range(1, 5))
                        # avoid duplicating a prop already captured
                        if not any(p["name"] == name and p["value"] == value for p in current["props"]):
                            current["props"].append({"name": name, "test": test, "unit": unit, "value": value})
                        continue
                    m2 = re.match(r"^(.{5,75}?)\s+([A-Za-z/°%0-9²³\. ]{1,14}?)\s+([<>]?[\d\.]+.*)$", s)
                    if m2:
                        prev_test = current["props"][-1]["test"] if current["props"] else ""
                        nm, un, vl = clean(m2.group(1)), clean(m2.group(2)), clean(m2.group(3))
                        if not any(p["name"] == nm and p["value"] == vl for p in current["props"]):
                            current["props"].append({"name": nm, "test": prev_test, "unit": un, "value": vl})
                        continue
                if in_proc:
                    m = re.match(r"^(Melt temperature|Mold temperature|Mould temperature|Melt Temperature|Mould Temperature|Processing temperatures?)(.*)$", s, re.I)
                    if m:
                        cond = "Processing Temperature" if m.group(1).lower().startswith("processing") else clean(m.group(1))
                        current["processing"].append({"condition": cond, "window": clean(m.group(2)).lstrip(": ")})
                    elif re.match(r"^Typical Process(?:ing)? Temperature", s):
                        m = re.search(r"Typical Process(?:ing)? Temperature:?\s*(.+)$", s)
                        if m:
                            current["processing"].append({"condition": "Typical Processing Temperature", "window": clean(m.group(1))})
                    elif not current["processing"] and re.match(r"^\d+\s*[-–]\s*\d+", s):
                        current["processing"].append({"condition": "Temperature", "window": clean(s)})
                elif in_apps:
                    if s.startswith(("•", "-", "\u2022")):
                        a = clean(s.lstrip("•- "))
                        if a:
                            current["applications"].append(a)
                    elif current["applications"] and not s.startswith(("Note", "The product", "Bags should", "Reliance Industries", "Updated as of", "*")):
                        current["applications"][-1] += " " + s
                    elif not current["applications"] and len(s) > 3 and not s.startswith(("Note", "The product", "Reliance Industries", "Updated as of")):
                        current["applications"].append(s)
            # also grab BIS if it's on this page and missing
            if not current["bis_code"]:
                bm = re.search(r"BIS Designation Code:?\s*([A-Z0-9:\- ]+)", text)
                if bm:
                    current["bis_code"] = clean(bm.group(1))

flush()

# Dedup: keep first occurrence of each grade
seen = {}
for g in grades:
    if g["grade"] not in seen:
        seen[g["grade"]] = g
grades = list(seen.values())

# --- Special fixup: B300MN (cover-style page with wrapped 2-col property layout) ---
for g in grades:
    if g["grade"] == "B300MN" and not g["props"]:
        g["polymer"] = "PP-Impact"
        g["brand_family"] = "Repol"
        g["application_segment"] = "Injection Moulding"
        g["desc"] = [
            "Repol B300MN is manufactured using Unipol PP process which combines the production efficiency of gas phase fluidized bed reactor technology with the high activity stereospecific catalyst system.",
            "Repol B300MN is high crystalline Impact Copolymer grade recommended for use in Injection Moulding processes. The grade contains nucleating agent.",
            "It is an ideal material for making automobile parts where high flow with very high stiffness is required. The grade is also suitable as a compounding base for automotive and appliance sectors.",
        ]
        g["applications"] = ["Automobile parts requiring high flow with very high stiffness",
                             "Compounding base for automotive and appliance sectors",
                             "Fast moulding cycle applications"]
        g["props"] = [
            {"name": "Melt Flow Rate (230°C/2.16 kg)", "test": "ASTM D1238", "unit": "g/10 min", "value": "30"},
            {"name": "Tensile Strength @ Yield (50 mm/min)", "test": "ASTM D638", "unit": "MPa", "value": "30"},
            {"name": "Elongation @ Yield (50 mm/min)", "test": "ASTM D638", "unit": "%", "value": "5"},
            {"name": "Flexural Modulus (1% secant, 1.3 mm/min)", "test": "ASTM D790A", "unit": "MPa", "value": "1650"},
            {"name": "Izod Impact Strength Notched @23°C", "test": "ASTM D256", "unit": "J/m", "value": "60"},
            {"name": "Charpy Impact @ 23°C", "test": "ASTM D256", "unit": "J/m", "value": "70"},
            {"name": "Heat Deflection Temperature (@ 455 KPa)", "test": "ASTM D648", "unit": "°C", "value": "115"},
        ]
        g["processing"] = []  # no processing window published in TDS

# Post-process: cut RIL footer text from applications; drop empty-value dupes
for g in grades:
    cleaned_apps = []
    for a in g["applications"]:
        for cut in ["Reliance Industries Limited", "Vadodara Manufacturing", "Gujarat, India",
                    "E-mail:", "Website:", "Pin 391346", "Updated as of", "P. O. Petrochemicals"]:
            a = re.split(re.escape(cut), a)[0]
        a = a.strip(" .,")
        if a and len(a) > 2:
            cleaned_apps.append(a)
    g["applications"] = cleaned_apps
    # drop props with garbage units like 'Test ISO'
    for p in g["props"]:
        if p["unit"] == "Test ISO":
            p["unit"] = "Hrs"
            p["test"] = "ISO 1167"
            p["name"] = p["name"].rstrip() + " Test" if not p["name"].endswith("Test") else p["name"]

# Normalize temperature windows: '180 – 220 OC' -> '180 - 220°C'
def norm_window(t):
    t = clean(t)
    t = t.replace("–", "-").replace("\u00ba", "°")
    t = re.sub(r"o\s*C\b", "°C", t, flags=re.I)
    t = re.sub(r"(\d+)0C\b", r"\1°C", t)
    t = re.sub(r"\s*OC\b", "°C", t)
    t = re.sub(r"\s+°C", "°C", t)
    t = re.sub(r"\s*-\s*", " - ", t)
    return t.strip(" :")

for g in grades:
    for pr in g["processing"]:
        pr["window"] = norm_window(pr["window"])
    g["processing"] = [pr for pr in g["processing"] if pr["window"]]

with open(OUT, "w") as f:
    json.dump(grades, f, indent=1)

print(f"Parsed {len(grades)} Reliance grades")
from collections import Counter
print(Counter(g["polymer"] for g in grades))
no_props = [g["grade"] for g in grades if len(g["props"]) < 4]
print("Grades with <4 props:", no_props)
no_proc = [g["grade"] for g in grades if not g["processing"]]
print(f"Grades w/o processing: {len(no_proc)}: {no_proc[:15]}")
no_apps = [g["grade"] for g in grades if not g["applications"]]
print(f"Grades w/o apps: {len(no_apps)}: {no_apps[:15]}")
