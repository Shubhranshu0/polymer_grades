#!/usr/bin/env python3
"""Parse Haldia September price lists (PE + PP) -> prices.json
Uses word x-positions to map stacked grade headers to price columns.
"""
import pdfplumber, json, re

def clean(s):
    if s is None:
        return ""
    return re.sub(r"\s+", " ", s).strip()

def parse_price_pdf(path, polymer_label):
    result = {"file": path.split("/")[-1], "polymer": polymer_label, "annexures": []}
    with pdfplumber.open(path) as pdf:
        # locate annexure sections by page text
        ann_pages = []
        for pn, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            m = re.search(r"Annexure\s*-\s*([IVX]+)", text)
            if m and ("PRICE LIST" in text or "EX-" in text):
                kind = "ex_works" if re.search(r"EX-\s*WORKS", text, re.I) else ("ex_stock" if re.search(r"EX-\s*STOCK", text, re.I) else "other")
                if "PRICE LIST" in text:
                    kind_m = re.search(r"(HDPE|LLDPE|PP)\s*:\s*PRICE LIST", text)
                    poly = kind_m.group(1) if kind_m else polymer_label
                    ann_pages.append((pn, m.group(1), poly, kind_m and re.search(r"EX-\s*WORKS", text, re.I)))
        # We'll parse each price table page: header zone (grades) + data rows
        for pn, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            if not re.search(r"PRICE POINTS", text):
                continue
            # classify this page
            poly_m = re.search(r"(HDPE|LLDPE|PP)\s*(?::|PRICE)", text)
            ex_type = "ex_works" if re.search(r"EX-\s*WORKS", text, re.I) else ("ex_stock" if re.search(r"EX-\s*STOCK", text, re.I) else "?")
            # circular + effective
            circ_m = re.search(r"Circular No:?\s*([A-Z0-9 /:\-]+)", text)
            eff_m = re.search(r"Effective:?\s*([\d\.]+)", text)

            words = page.extract_words()
            # find header zone: between "(Rs./MT)" anchor and "PRICE POINTS"
            pp_top = None
            rsmt_top = None
            for w in words:
                if w["text"] == "PRICE" and w["top"] > 100:
                    pp_top = w["top"]
                    break
            for w in words:
                if "(Rs./MT)" in w["text"]:
                    rsmt_top = w["top"]
                    break
            if pp_top is None:
                continue
            zone_lo = (rsmt_top + 4) if rsmt_top else 60
            # grade header words: between zone anchor and PRICE POINTS
            hdr_words = [w for w in words if zone_lo < w["top"] < pp_top - 3 and w["x0"] > 100]
            # group into lines by top
            lines = {}
            for w in hdr_words:
                lines.setdefault(round(w["top"]), []).append(w)
            # collect grade tokens with x-centers
            grade_cells = []  # (xc, name)
            for top in sorted(lines):
                toks = sorted(lines[top], key=lambda w: w["x0"])
                # merge adjacent words of same grade (like 'HD OG (E)')
                merged = []
                for w in toks:
                    if merged and abs(w["x0"] - merged[-1]["x1"]) < 4 and abs(w["top"] - merged[-1]["top"]) < 2:
                        merged[-1] = {"text": merged[-1]["text"] + " " + w["text"],
                                      "x0": merged[-1]["x0"], "x1": w["x1"], "top": merged[-1]["top"]}
                    else:
                        merged.append(dict(w))
                for w in merged:
                    grade_cells.append(((w["x0"] + w["x1"]) / 2, clean(w["text"]), top))
            # filter out non-grade tokens
            NON_GRADE = {"Ex-Works", "Basic", "Price", "(Rs./MT)", "Grades", "BASIC", "PRICE", "PRICE POINTS", "Ex-", "Works", ":", "Price", "List"}
            grade_cells = [g for g in grade_cells if g[1] not in NON_GRADE and not re.match(r"^\(", g[1]) and g[1] not in ("HDPE", "LLDPE", "PP", "EX-WORKS", "EX-STOCK")]

            # cluster grade cells into columns by x-center
            columns = []  # list of {"xc": float, "grades": [names]}
            for xc, name, top in sorted(grade_cells, key=lambda g: g[2]):
                placed = False
                for col in columns:
                    if abs(col["xc"] - xc) < 12:
                        col["grades"].append(name)
                        col["xc"] = (col["xc"] + xc) / 2
                        placed = True
                        break
                if not placed:
                    columns.append({"xc": xc, "grades": [name]})
            columns.sort(key=lambda c: c["xc"])

            # data rows: words below pp_top, group by line
            data_lines = {}
            for w in words:
                if w["top"] > pp_top + 2:
                    data_lines.setdefault(round(w["top"]), []).append(w)

            rows = []
            for top in sorted(data_lines):
                toks = sorted(data_lines[top], key=lambda w: w["x0"])
                # first token(s): location name (may contain spaces) until first numeric token
                loc_parts = []
                vals = []
                for w in toks:
                    if re.match(r"^[\d,\.]+$", w["text"]):
                        vals.append((w["x0"], w["text"]))
                    else:
                        if vals:
                            # location shouldn't come after values (except trailing like 'HPL')
                            loc_parts.append(w["text"]) if not vals else None
                        else:
                            loc_parts.append(w["text"])
                if vals and loc_parts:
                    loc = clean(" ".join(loc_parts))
                    if loc and loc.upper() != "BASIC PRICE":
                        rows.append({"location": loc, "values": vals})

            # map values to columns by x0
            table = []
            for r in rows:
                prices = {}
                for x0, v in r["values"]:
                    # find nearest column
                    best, bestd = None, 1e9
                    for col in columns:
                        d = abs(col["xc"] - x0)
                        if d < bestd:
                            best, bestd = col, d
                    if best is not None:
                        for gname in best["grades"]:
                            prices[gname] = v.replace(",", "")
                table.append({"location": r["location"], "prices": prices})

            result["annexures"].append({
                "page": pn + 1,
                "type": ex_type,
                "polymer": poly_m.group(1) if poly_m else polymer_label,
                "circular": clean(circ_m.group(1)) if circ_m else "",
                "effective": clean(eff_m.group(1)) if eff_m else "",
                "columns": [c["grades"] for c in columns],
                "table": table,
            })
    return result

pe = parse_price_pdf("/home/z/my-project/upload/Polyethylene Price-September Price.pdf", "PE")
pp = parse_price_pdf("/home/z/my-project/upload/Polypropylene Price-September Month.pdf", "PP")

out = {"pe": pe, "pp": pp}
with open("/home/z/my-project/extracted/prices.json", "w") as f:
    json.dump(out, f, indent=1)

for doc in (pe, pp):
    print(f"\n=== {doc['file']}: {len(doc['annexures'])} price tables")
    for a in doc["annexures"]:
        print(f"  p{a['page']} {a['type']} {a['polymer']} cols={len(a['columns'])} rows={len(a['table'])} eff={a['effective']}")
        print(f"    columns: {a['columns'][:12]}")
        if a["table"]:
            t0 = a["table"][0]
            print(f"    first row: {t0['location']} -> {list(t0['prices'].items())[:6]}")
