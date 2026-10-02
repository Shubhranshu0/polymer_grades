#!/usr/bin/env python3
"""Assemble unified dataset for the SHLOK Polymer Grade Book website.
Inputs: haldia.json, iocl.json, reliance.json, ongc.json, prices_raw.json, competition.json
Output: /home/z/my-project/extracted/dataset.json
"""
import json, re, unicodedata

BASE = "/home/z/my-project/extracted"

def load(name):
    with open(f"{BASE}/{name}") as f:
        return json.load(f)

haldia = load("haldia.json")
iocl = load("iocl.json")
reliance = load("reliance.json")
ongc = load("ongc.json")
prices_raw = load("prices_raw.json")
competition = load("competition.json")

COMPANIES = {
    "haldia": {"name": "Haldia Petrochemicals Ltd", "short": "HPL", "city": "Haldia, West Bengal",
               "brands": ["Halene H", "Halene L", "Halene P"],
               "color": "#C8102E", "note": "Producer of the Halene polymer range (HDPE, LLDPE, PP)"},
    "reliance": {"name": "Reliance Industries Ltd", "short": "RIL", "city": "Vadodara, Gujarat",
                 "brands": ["Relene", "Relpure", "Repol"],
                 "color": "#0F4C81", "note": "India's largest polymer producer - Relene PE and Repol PP ranges"},
    "iocl": {"name": "Indian Oil Corporation Ltd", "short": "IOCL", "city": "Panipat / Paradip",
             "brands": ["Propel"],
             "color": "#F26522", "note": "Propel brand polymers from Panipat Naphtha Cracker and Paradip units"},
    "ongc": {"name": "ONGC Petro Additions Ltd", "short": "OPaL", "city": "Dahej, Gujarat",
             "brands": ["OPaL"],
             "color": "#2E7D32", "note": "OPaL Dahej complex - HDPE (Mitsui CX), LLDPE (Ineos) and PP (Ineos)"},
}

POLYMER_LABELS = {
    "HDPE": "High-Density Polyethylene",
    "LLDPE": "Linear Low-Density Polyethylene",
    "LDPE": "Low-Density Polyethylene",
    "PP-Homo": "PP Homopolymer",
    "PP-Random": "PP Random Copolymer",
    "PP-Impact": "PP Impact Copolymer",
    "PP": "Polypropylene",
}

# ---------------- key property extraction ----------------
def norm_txt(s):
    s = s or ""
    s = s.replace("\u2013", "-").replace("\u00b2", "2").replace("\u00b3", "3")
    return re.sub(r"\s+", " ", s).strip()

def extract_key_props(props):
    mfi = density = tensile = flex = izod = None
    for p in props:
        n = norm_txt(p.get("name", "")).lower()
        v = norm_txt(p.get("value", ""))
        u = norm_txt(p.get("unit", ""))
        if not v:
            continue
        if "melt flow" in n and mfi is None:
            cond = ""
            m = re.search(r"\(([^)]*)\)", norm_txt(p.get("name", "")))
            if m:
                cond = m.group(1)
            mfi = {"value": v, "unit": u or "g/10 min", "condition": cond}
        elif "density" in n and density is None:
            density = {"value": v, "unit": u or "g/cm3"}
        elif "tensile strength" in n and "yield" in n and tensile is None:
            tensile = {"value": v, "unit": u or "MPa"}
        elif "flexural" in n and flex is None:
            flex = {"value": v, "unit": u or "MPa"}
        elif "izod" in n and izod is None:
            izod = {"value": v, "unit": u or "J/m"}
    return {"mfi": mfi, "density": density, "tensile_yield": tensile, "flexural": flex, "izod": izod}

# ---------------- segment derivation ----------------
SEGMENT_RULES = [
    (r"\braffia\b|stretched tape|\bwoven\b", "Raffia / Stretched Tape"),
    (r"\bmonofilament\b|\byarns?\b|\bropes?\b|\btwines?\b|\bnets?\b|\bmosquito\b", "Monofilament / Yarn"),
    (r"\bbopp\b|biaxially", "BOPP Film"),
    (r"\btqpp\b|tubular water quench|\btq ?\(", "TQPP Film"),
    (r"\bcast film\b", "Cast Film"),
    (r"\blamination\b|extrusion coating|\bcoat\b", "Extrusion Coating / Lamination"),
    (r"\bducts?\b|\bpipe\b|pe80|pe100|pe63|\bconduit\b", "Pipe Extrusion"),
    (r"drip lateral|\birrigation\b", "Drip Irrigation Pipe"),
    (r"blow mould|blow mold|\bcontainer\b|\bbottle\b|\bdrums?\b|\bfuel\b|\bbarrel\b|\bjerrycan\b", "Blow Moulding"),
    (r"caps? (?:&|and) closures?|\bclosures?\b|\bcrown\b", "Caps & Closures"),
    (r"\binjection\b|\bthin[- ]wall\b|\bhouseware\b|\bcrates?\b", "Injection Moulding"),
    (r"\bfilm\b|carrier bag|\bpackaging\b|\bbags\b", "Film"),
    (r"\broto\b|water tank|\btanks?\b", "Rotational Moulding"),
    (r"\bmasterbatch\b|\bcompounding\b|\bcompounds?\b", "Masterbatch / Compounding"),
    (r"\bfibres?\b|\bfibers?\b|\bfilaments?\b|non-?woven|\bspun\b", "Fibre / Non-Woven"),
    (r"\bcable\b|\bxlpe\b|\bjacket\b|\bsheath\b", "Cable / XLPE"),
]

def derive_segment(seg, desc, uses, grade=""):
    text = " ".join([seg or "", " ".join(desc or []), " ".join(uses or []), grade]).lower()
    for pat, label in SEGMENT_RULES:
        if re.search(pat, text):
            return label
    return seg or "General Purpose"

# ---------------- grade normalization ----------------
def norm_grade_data(g, company_id):
    props = []
    for p in g.get("props", []):
        n = norm_txt(p.get("name"))
        if not n or n.lower() in ("property", "physical property", "mechanical properties", "thermal properties"):
            continue
        props.append({
            "name": n,
            "test": norm_txt(p.get("test", "")),
            "unit": norm_txt(p.get("unit", "")),
            "value": norm_txt(p.get("value", "")),
        })
    # filter junk processing rows
    proc = []
    for pr in g.get("processing", []):
        c = norm_txt(pr.get("condition", ""))
        w = norm_txt(pr.get("window", ""))
        if not c or not w:
            continue
        if re.match(r"^(ARDC|VER\s?\d|Note)", c, re.I):
            continue
        proc.append({"condition": c, "window": w})
    desc = [norm_txt(d) for d in g.get("desc", []) if norm_txt(d) and len(norm_txt(d)) > 3]
    uses = [norm_txt(u) for u in g.get("applications", []) if norm_txt(u) and len(norm_txt(u)) > 2]
    # ONGC app cleanup: drop 'Datasheet <title>' bleed before first wingding bullet
    uses = [re.sub(r"[\uf0b7\uf0fc\uf0a7]", ";", u) for u in uses]
    uses2 = []
    for u in uses:
        parts = [p.strip(" .,") for p in re.split(r";", u)]
        if parts and parts[0].startswith("Datasheet"):
            parts = parts[1:]
        for part in parts:
            if part and len(part) > 2 and not part.lower().startswith(("datasheet", "note")):
                uses2.append(part)
    uses = uses2
    # Haldia: derive uses from desc ("recommended for ...", "can be used for/in ...")
    if not uses:
        for d in desc:
            m = re.search(r"(?:is |are )?(?:particularly )?recommended for ([^.]+)", d, re.I)
            if m:
                uses.append(norm_txt(m.group(1)).strip(" ."))
            m = re.search(r"can be used (?:for|in) ([^.]+)", d, re.I)
            if m:
                uses.append(norm_txt(m.group(1)).strip(" ."))
        uses = list(dict.fromkeys(u for u in uses if u))[:6]
    seg = derive_segment(g.get("application_segment", ""), desc, uses, g.get("grade", ""))
    key = extract_key_props(props)
    return {
        "id": f"{company_id}-{re.sub(r'[^A-Za-z0-9]+', '-', g['grade']).strip('-').lower()}",
        "company": company_id,
        "company_name": COMPANIES[company_id]["name"],
        "grade": norm_txt(g.get("grade", "")),
        "polymer": g.get("polymer", ""),
        "polymer_label": POLYMER_LABELS.get(g.get("polymer", ""), g.get("polymer", "")),
        "family": norm_txt(g.get("brand_family", "")),
        "segment": seg,
        "desc": desc,
        "uses": uses,
        "bis_code": norm_txt(g.get("bis_code", "")),
        "key": key,
        "props": props,
        "processing": proc,
        "alt_codes": g.get("alt_codes", []),
    }

grades = []
for g in haldia:
    grades.append(norm_grade_data(g, "haldia"))
for g in reliance:
    grades.append(norm_grade_data(g, "reliance"))
for g in iocl:
    grades.append(norm_grade_data(g, "iocl"))
for g in ongc:
    grades.append(norm_grade_data(g, "ongc"))

# dedup by id
seen = {}
for g in grades:
    if g["id"] not in seen:
        seen[g["id"]] = g
grades = list(seen.values())

# ---------------- price consolidation ----------------
def merge_tables(pages, polys, types):
    """Merge multi-page price tables of same polymer+type. Returns (columns, rows dict loc->prices)."""
    merged_rows = {}
    columns = None
    for p in pages:
        pr = p["parsed"]
        if pr.get("side_by_side"):
            # left = ex_works, right = ex_stock
            lcols, ltable = pr["left"]
            rcols, rtable = pr["right"]
            src = ltable if types == "ex_works" else rtable
            cols = lcols if types == "ex_works" else rcols
        else:
            cols, src = pr["table"]
        if types == "ex_works" and pr.get("side_by_side") is False and p["type"] == "ex_stock":
            continue
        if columns is None:
            columns = cols
        for r in src:
            loc = r["location"]
            if loc not in merged_rows:
                merged_rows[loc] = {}
            merged_rows[loc].update(r["prices"])
    return columns, merged_rows

def build_price_doc(raw_doc, polymer_keys):
    """raw_doc: prices_raw['pe'] etc. Returns structured price data."""
    doc = {"circular": "", "effective": ""}
    pages = raw_doc["pages"]
    # fill circular/effective; carry forward polymer/type for continuation pages
    last_poly, last_type = "", ""
    for p in pages:
        if p["circular"]:
            doc["circular"] = p["circular"]
        if p["effective"]:
            doc["effective"] = p["effective"]
        if p["polymer"]:
            last_poly = p["polymer"]
        else:
            p["polymer"] = last_poly
        if p["type"] and p["type"] != "?":
            last_type = p["type"]
        p["eff_type"] = p["type"] if p["type"] and p["type"] != "?" else last_type
    for pk in polymer_keys:
        pset = [p for p in pages if p["polymer"] == pk]
        if not pset:
            continue
        for typ in ("ex_works", "ex_stock"):
            tset = []
            for p in pset:
                pr = p["parsed"]
                if pr.get("side_by_side"):
                    tset.append(p)  # contains both (left=ex_works, right=ex_stock)
                elif p["eff_type"] == typ:
                    tset.append(p)
            if not tset:
                continue
            cols, rows = merge_tables(tset, pk, typ)
            if not rows:
                continue
            grade_summary = {}
            for col in cols:
                for gname in col["grades"]:
                    vals = [r.get(gname) for r in rows.values() if r.get(gname)]
                    if vals:
                        nums = sorted(int(v) for v in vals if v.isdigit())
                        if nums:
                            grade_summary[gname] = {
                                "min": nums[0], "max": nums[-1],
                                "ref": int(list(rows.values())[0].get(gname, 0)) or nums[0],
                            }
            matrix = [{"location": loc, "prices": prices} for loc, prices in rows.items()]
            doc.setdefault(pk, {})[typ] = {
                "columns": [c["grades"] for c in cols],
                "matrix": matrix,
                "summary": grade_summary,
            }
    return doc

pe_price = build_price_doc(prices_raw["pe"], ["HDPE", "LLDPE"])
pp_price = build_price_doc(prices_raw["pp"], ["PP"])

# match prices to Haldia grades
def match_price_to_grades(grade_summary):
    out = {}
    for gname, info in grade_summary.items():
        out[gname] = info
    return out

def find_price_for_grade(grade, pe_doc, pp_doc):
    """Match a Haldia grade name to a price column (handles grouped names)."""
    candidates = []
    for doc, polys in ((pe_doc, ("HDPE", "LLDPE")), (pp_doc, ("PP",))):
        for pk in polys:
            if pk not in doc:
                continue
            for typ in ("ex_works", "ex_stock"):
                sec = doc[pk].get(typ)
                if not sec:
                    continue
                # direct match within a group name
                for gname, info in sec["summary"].items():
                    gn = gname.upper().replace(" ", "")
                    gu = grade.upper().replace(" ", "").replace("-", "")
                    if gn == gu or gu in gn:
                        candidates.append({"type": typ, "polymer": pk, **info})
    return candidates

for g in grades:
    if g["company"] != "haldia":
        continue
    cands = find_price_for_grade(g["grade"], pe_price, pp_price)
    if cands:
        ew = next((c for c in cands if c["type"] == "ex_works"), cands[0])
        g["price"] = {
            "ex_works_min": ew.get("min"),
            "ex_works_max": ew.get("max"),
            "ex_works_ref": ew.get("ref"),
            "currency": "Rs./MT",
            "effective": pe_price.get("effective") if ew.get("polymer") in ("HDPE", "LLDPE") else pp_price.get("effective"),
        }

# ---------------- competition data ----------------
comp_records = []
COMP_SHEET_KEYS = {"IOCL": "iocl", "RELIANCE-": "reliance", "ONGC": "ongc", "RELIANCE": "reliance"}
for sheet, d in competition.items():
    if sheet not in COMP_SHEET_KEYS:
        continue
    hdr = d["header"]
    # pad header to 15
    for r in d["rows"]:
        rec = {}
        for i, v in enumerate(r[:len(hdr)]):
            key = hdr[i] if i < len(hdr) and hdr[i] else f"col{i}"
            rec[key] = v
        # normalize keys
        comp_records.append({
            "company": COMP_SHEET_KEYS[sheet],
            "company_label": r[0] if r[0] else sheet,
            "polymer": r[1] if len(r) > 1 else "",
            "grade": r[2] if len(r) > 2 else "",
            "moulding": r[3] if len(r) > 3 else "",
            "key_props": r[4] if len(r) > 4 else "",
            "superior": r[5] if len(r) > 5 else "",
            "apps": r[6] if len(r) > 6 else "",
            "other_apps": r[7] if len(r) > 7 else "",
            "limitations": r[8] if len(r) > 8 else "",
            "processing": r[9] if len(r) > 9 else "",
            "technology": r[10] if len(r) > 10 else "",
            "haldia_alt": r[11] if len(r) > 11 else "",
            "comparison": r[12] if len(r) > 12 else "",
            "reason_haldia_better": r[13] if len(r) > 13 else "",
            "haldia_grade_superior": r[14] if len(r) > 14 else "",
        })

# link competition to grade records
comp_by_key = {}
for c in comp_records:
    comp_by_key[(c["company"], c["grade"].upper())] = c
for g in grades:
    c = comp_by_key.get((g["company"], g["grade"].upper()))
    if c:
        g["competition"] = {
            "key_props": c["key_props"],
            "superior": c["superior"],
            "limitations": c["limitations"],
            "haldia_alt": c["haldia_alt"],
            "comparison": c["comparison"],
            "reason_haldia_better": c["reason_haldia_better"],
            "haldia_grade_superior": c["haldia_grade_superior"],
        }

# ---------------- B300MN (not in competition sheet) — auto-map by TDS profile ----------------
# Reliance B300MN is a nucleated high-crystalline ICP, MFI 30. Haldia M330 is the
# nucleated ICP with the same MFI 30 — closest match. Flagged as auto-mapped.
grade_by_id = {g["id"]: g for g in grades}
AUTO_ALT = {
    ("reliance", "B300MN"): {
        "haldia_alt": "M330",
        "note": "Auto-mapped: closest Haldia grade by TDS profile (both nucleated PP impact copolymers, MFI 30). "
                "This grade is not present in the uploaded competition sheet.",
        "comparison": "Repol B300MN (MFI 30, flexural 1650 MPa, Izod 60 J/m) lines up with Haldia M330 "
                      "(MFI 30, nucleated impact copolymer for thin-wall and houseware injection moulding).",
    },
}
for (company, grade_name), spec in AUTO_ALT.items():
    g = next((x for x in grades if x["company"] == company and x["grade"] == grade_name), None)
    if g and not g.get("competition"):
        g["competition"] = {
            "key_props": "", "superior": "", "limitations": "",
            "haldia_alt": spec["haldia_alt"],
            "comparison": spec["comparison"],
            "reason_haldia_better": spec["note"],
            "haldia_grade_superior": "",
        }
        g["competition"]["auto_mapped"] = True

# ---------------- structured alternate-Haldia-grade links ----------------
# The Excel's "Alternative Application (Haldia Grade)" column is free text like
# "M365 & M340" or "HDT10 & HDT10S" or "HD T9 (tape/raffia) and HD T10S" —
# extract every referenced Haldia grade code and link it to the real grade id.
haldia_grade_list = [g for g in grades if g["company"] == "haldia"]

def find_haldia_refs(text):
    if not text:
        return []
    refs = []
    for hg in haldia_grade_list:
        code = hg["grade"]
        pat = r"\b" + re.escape(code).replace(r"\ ", r"\s*") + r"\b"
        m = re.search(pat, text, re.I)
        if m:
            refs.append((m.start(), hg["grade"], hg["id"]))
    refs.sort(key=lambda x: x[0])
    out, seen = [], set()
    for _, gd, gid in refs:
        if gd not in seen:
            seen.add(gd)
            out.append({"grade": gd, "id": gid})
    return out

def classify_alt(text):
    t = (text or "").strip().lower()
    if not t or t == "n/a":
        return "none"
    if t.startswith("no ") or "closest" in t or "nearest" in t or "not an equivalent" in t:
        return "closest"
    return "direct"

for g in grades:
    if g["company"] == "haldia" or not g.get("competition"):
        continue
    c = g["competition"]
    refs = find_haldia_refs(c.get("haldia_alt", ""))
    alt_text = (c.get("haldia_alt") or "").strip()
    declines = alt_text.lower().startswith("no ") or alt_text.lower() == "n/a"
    if not refs and declines:
        # text explicitly offers no substitute — ignore grades merely mentioned in notes
        secondary = []
        kind = "none"
    else:
        # also scan comparison/reason text for extra referenced grades (secondary matches)
        secondary = [r for r in find_haldia_refs((c.get("comparison") or "") + " " + (c.get("haldia_grade_superior") or "")) if r["grade"] not in {x["grade"] for x in refs}]
        kind = classify_alt(alt_text)
        if not refs and not secondary:
            kind = "none"
    c["alt_haldia_ids"] = refs
    c["alt_haldia_secondary"] = secondary
    c["alt_match_kind"] = kind
    c["alt_note"] = alt_text if c["alt_match_kind"] == "closest" else ""

# ---------------- reverse map: which competitor grades compete with each Haldia grade ----------------
for g in grades:
    if g["company"] == "haldia":
        g["competed_by"] = []
for g in grades:
    if g["company"] == "haldia" or not g.get("competition"):
        continue
    kind = g["competition"].get("alt_match_kind", "none")
    for ref in g["competition"].get("alt_haldia_ids", []):
        hg = grade_by_id.get(ref["id"])
        if hg:
            hg.setdefault("competed_by", []).append({
                "company": g["company"],
                "grade": g["grade"],
                "id": g["id"],
                "polymer": g["polymer"],
                "kind": kind,
            })
    for ref in g["competition"].get("alt_haldia_secondary", []):
        hg = grade_by_id.get(ref["id"])
        if hg:
            hg.setdefault("competed_by", []).append({
                "company": g["company"],
                "grade": g["grade"],
                "id": g["id"],
                "polymer": g["polymer"],
                "kind": "secondary",
            })

# assumptions sheet
assumptions = []
for r in competition.get("Assumptions & Data Gaps", {}).get("rows", []):
    line = " ".join(v for v in r if v)
    if line and line != "#":
        assumptions.append(line)

# ---------------- final assembly ----------------
from collections import Counter, defaultdict
counts = defaultdict(lambda: Counter())
for g in grades:
    counts[g["company"]][g["polymer"]] += 1

dataset = {
    "meta": {
        "generated": "2026-09-17",
        "source_pdfs": [
            "Haldia Polymer merged.pdf (ARDC TDS book, 110 pages)",
            "Reliance Polymer merged.pdf (Relene / Relpure / Repol TDS, 209 pages)",
            "IOCL All Polymer TDS.pdf (Propel TDS, 70 pages)",
            "ONGC POLYMER.pdf (OPaL provisional TDS, 56 pages)",
            "Polyethylene Price-September Price.pdf (HPL circular 101, eff. 07.09.2026)",
            "Polypropylene Price-September Month.pdf (HPL circular 100, eff. 05.09.2026)",
            "POLYMER COMPETITION.xlsx (grade-vs-grade competitive analysis)",
        ],
        "total_grades": len(grades),
        "grade_counts": {k: dict(v) for k, v in counts.items()},
    },
    "companies": COMPANIES,
    "polymer_labels": POLYMER_LABELS,
    "grades": grades,
    "prices": {"pe": pe_price, "pp": pp_price},
    "competition_notes": assumptions,
}

with open(f"{BASE}/dataset.json", "w") as f:
    json.dump(dataset, f, indent=1, ensure_ascii=False)

print(f"Total grades: {len(grades)}")
for k, v in counts.items():
    print(f"  {k}: {sum(v.values())} {dict(v)}")
print(f"Competition records: {len(comp_records)}")
priced = [g for g in grades if g.get("price")]
print(f"Haldia grades with price: {len(priced)}/56")
print("Assumptions:", len(assumptions))
# sample
for gid in ["haldia-hd-t9", "reliance-h110ma", "iocl-002db52", "ongc-b55h02"]:
    g = next((x for x in grades if x["id"] == gid), None)
    if g:
        print("\n" + "=" * 60)
        print(g["id"], "|", g["grade"], "|", g["polymer"], "|", g["segment"])
        print("  MFI:", g["key"]["mfi"], "| Density:", g["key"]["density"])
        print("  uses:", g["uses"][:2])
        if g.get("price"):
            print("  price:", g["price"])
        if g.get("competition"):
            print("  comp alt:", g["competition"]["haldia_alt"])
