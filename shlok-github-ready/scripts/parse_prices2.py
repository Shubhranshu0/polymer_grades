#!/usr/bin/env python3
"""Parse Haldia September price lists (PE + PP) -> prices.json (v2)
Structure per PDF page set:
  - Header zone between '(Rs./MT)' anchor and 'Grades' label
  - Data rows after 'Grades'
  - LLDPE table is side-by-side: Ex-Works (left) | Ex-Stock Point (right)
"""
import pdfplumber, json, re

def clean(s):
    if s is None:
        return ""
    return re.sub(r"\s+", " ", s).strip()

NON_GRADE = {"Ex-Works", "Basic", "Price", "(Rs./MT)", "Grades", "BASIC", "PRICE",
             "PRICE POINTS", "Ex-", "Works", ":", "List", "Ex-Stocks", "Ex-Stock",
             "Stock", "Point", "Basic Price", "BASIC PRICE", "Ex-Works Price",
             "Ex-Stock Point Price", "Ex-Stocks Basic Price"}

def merge_tokens(toks):
    """Merge adjacent words on the same line into grade names, capped at 36px span
    (handles 'HD OG (E)' 22px; avoids merging 'M6007L'+'M6007LU' 41px)."""
    merged = []
    for w in toks:
        if merged:
            prev = merged[-1]
            gap = w["x0"] - prev["x1"]
            span = w["x1"] - prev["x0"]
            if gap < 5 and span <= 36 and abs(w["top"] - prev["top"]) < 3:
                prev["text"] = prev["text"] + " " + w["text"]
                prev["x1"] = w["x1"]
                continue
        merged.append(dict(w))
    return merged

STANDALONE_RE = re.compile(r"^[A-Z]{1,4}[0-9][A-Z0-9\-/]*$")

def parse_columns(hdr_words):
    lines = {}
    for w in hdr_words:
        lines.setdefault(round(w["top"] / 2), []).append(w)
    cells = []
    for key in sorted(lines):
        toks = sorted(lines[key], key=lambda w: w["x0"])
        for w in merge_tokens(toks):
            t = clean(w["text"])
            if t and t not in NON_GRADE and not re.match(r"^[\d\-]+$", t):
                cells.append(((w["x0"] + w["x1"]) / 2, t, w["top"]))
    columns = []
    for xc, name, top in sorted(cells, key=lambda c: c[2]):
        placed = False
        for col in columns:
            if abs(col["xc"] - xc) < 14:
                if name not in col["grades"]:
                    col["grades"].append(name)
                placed = True
                break
        if not placed:
            columns.append({"xc": xc, "grades": [name]})
    # join composite fragment names: only when ALL items are fragments (e.g. '3-4 MI' + 'HP Pwd')
    for col in columns:
        if col["grades"] and all(not STANDALONE_RE.match(g) for g in col["grades"]):
            composite = " ".join(col["grades"])
            composite = re.sub(r"\s*[-–]\s*", "-", composite)
            col["grades"] = [composite]
    return columns

def parse_page(page):
    text = page.extract_text() or ""
    words = page.extract_words()
    rsmt_words = [w for w in words if "(Rs./MT)" in w["text"]]
    if not rsmt_words:
        return None
    rsmt_top = min(w["top"] for w in rsmt_words)

    # detect side-by-side: two (Rs./MT) anchors far apart horizontally
    side_by_side = False
    split_x = page.width / 2
    if len(rsmt_words) >= 2:
        xs = sorted(w["x0"] for w in rsmt_words)
        if xs[-1] - xs[0] > 150:
            side_by_side = True
            split_x = (xs[-1] + xs[0]) / 2 + 5

    # find header end: first line below rsmt_top containing a pure numeric price token (5+ digits)
    data_top = None
    by_line = {}
    for w in words:
        if w["top"] > rsmt_top:
            by_line.setdefault(round(w["top"]), []).append(w)
    for top in sorted(by_line):
        if any(re.match(r"^\d{5,}$", w["text"].replace(",", "")) for w in by_line[top]):
            data_top = top
            break
    if data_top is None:
        return None

    hdr_words = [w for w in words if rsmt_top + 4 < w["top"] < data_top - 2 and w["x0"] > 100]
    data_words = [w for w in words if w["top"] >= data_top - 2]

    def build_result(half_words, data_all=None):
        columns = parse_columns(half_words)
        return columns

    if side_by_side:
        lcols = parse_columns([w for w in hdr_words if w["x0"] < split_x])
        rcols = parse_columns([w for w in hdr_words if w["x0"] >= split_x])
        # data lines across the full page; location from left part, prices split by x
        ltable, rtable = [], []
        dlines = {}
        for w in data_words:
            dlines.setdefault(round(w["top"]), []).append(w)
        for top in sorted(dlines):
            toks = sorted(dlines[top], key=lambda w: w["x0"])
            loc_parts = []
            lvals, rvals = [], []
            for w in toks:
                if re.match(r"^[\d,\.]+$", w["text"]):
                    if w["x0"] < split_x:
                        lvals.append((w["x0"], w["text"].replace(",", "")))
                    else:
                        rvals.append((w["x0"], w["text"].replace(",", "")))
                elif w["x0"] < split_x and not lvals and not rvals:
                    loc_parts.append(w["text"])
            loc = clean(" ".join(loc_parts))
            if (lvals or rvals) and loc and loc.upper() not in ("PRICE POINTS", "BASIC PRICE"):
                def map_vals(vals, cols):
                    prices = {}
                    for x0, v in vals:
                        best, bestd = None, 1e9
                        for col in cols:
                            d = abs(col["xc"] - x0)
                            if d < bestd:
                                best, bestd = col, d
                        if best is not None and bestd < 20:
                            for g in best["grades"]:
                                prices[g] = v
                    return prices
                ltable.append({"location": loc, "prices": map_vals(lvals, lcols)})
                rtable.append({"location": loc, "prices": map_vals(rvals, rcols)})
        return {"side_by_side": True, "left": (lcols, ltable), "right": (rcols, rtable)}
    else:
        cols = parse_columns(hdr_words)
        table = []
        dlines = {}
        for w in data_words:
            dlines.setdefault(round(w["top"]), []).append(w)
        for top in sorted(dlines):
            toks = sorted(dlines[top], key=lambda w: w["x0"])
            loc_parts, vals = [], []
            for w in toks:
                if re.match(r"^[\d,\.]+$", w["text"]):
                    vals.append((w["x0"], w["text"].replace(",", "")))
                elif not vals:
                    loc_parts.append(w["text"])
            loc = clean(" ".join(loc_parts))
            if vals and loc and loc.upper() not in ("PRICE POINTS", "BASIC PRICE"):
                prices = {}
                for x0, v in vals:
                    best, bestd = None, 1e9
                    for col in cols:
                        d = abs(col["xc"] - x0)
                        if d < bestd:
                            best, bestd = col, d
                    if best is not None and bestd < 20:
                        for g in best["grades"]:
                            prices[g] = v
                table.append({"location": loc, "prices": prices})
        return {"side_by_side": False, "table": (cols, table)}

def doc_summary(path, polymer_label):
    with pdfplumber.open(path) as pdf:
        pages_data = []
        for pn, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            ann_m = re.search(r"Annexure\s*-\s*([IVX]+)", text)
            circ_m = re.search(r"Circular\s*No:?\s*([A-Z0-9 /:\-]+)", text)
            eff_m = re.search(r"Effective:?\s*([\d\.]+)", text)
            poly_m = re.search(r"(HDPE|LLDPE|PP)\s*:\s*PRICE LIST", text)
            extype = "ex_stock" if re.search(r"EX-\s*STOCK", text, re.I) else "ex_works"
            parsed = parse_page(page)
            if parsed and ((parsed.get("table") and parsed["table"][1]) or parsed.get("side_by_side")):
                pages_data.append({
                    "page": pn + 1,
                    "annexure": ann_m.group(1) if ann_m else "",
                    "type": extype,
                    "polymer": poly_m.group(1) if poly_m else "",
                    "circular": clean(circ_m.group(1)) if circ_m else "",
                    "effective": clean(eff_m.group(1)) if eff_m else "",
                    "parsed": parsed,
                })
    return {"file": path.split("/")[-1], "polymer": polymer_label, "pages": pages_data}

pe = doc_summary("/home/z/my-project/upload/Polyethylene Price-September Price.pdf", "PE")
pp = doc_summary("/home/z/my-project/upload/Polypropylene Price-September Month.pdf", "PP")

out = {"pe": pe, "pp": pp}
with open("/home/z/my-project/extracted/prices_raw.json", "w") as f:
    json.dump(out, f, indent=1)

for doc in (pe, pp):
    print(f"\n=== {doc['file']}")
    for p in doc["pages"]:
        pr = p["parsed"]
        if pr["side_by_side"]:
            lcols, ltable = pr["left"]
            rcols, rtable = pr["right"]
            print(f"  p{p['page']} ANNEX-{p['annexure']} {p['type']} {p['polymer']} | LEFT {len(lcols)} cols x {len(ltable)} rows | RIGHT {len(rcols)} cols x {len(rtable)} rows")
            if ltable:
                print(f"    left cols: {[c['grades'] for c in lcols][:8]}")
                print(f"    left first: {ltable[0]['location']} {list(ltable[0]['prices'].items())[:4]}")
        else:
            cols, table = pr["table"]
            print(f"  p{p['page']} ANNEX-{p['annexure']} {p['type']} {p['polymer']} | {len(cols)} cols x {len(table)} rows | eff={p['effective']}")
            if table:
                print(f"    cols: {[c['grades'] for c in cols][:8]}")
                print(f"    first: {table[0]['location']} {list(table[0]['prices'].items())[:4]}")
