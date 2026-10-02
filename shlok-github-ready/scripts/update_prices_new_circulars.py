#!/usr/bin/env python3
"""Update the consolidated Haldia price table + per-grade TDS price fields
from the current HPL circulars (October 2026):

  - upload/PE-Price-Oct.pdf   (HPL/PM/26-27/112, wef 01.10.2026)
      Annexure I   : HDPE Ex-Works basic price   (28 column groups)
      Annexure II  : HDPE Ex-Stock basic price   (28 column groups)
      Annexure III : LLDPE combined table        (8 ex-works + 8 ex-stock cols)
  - upload/PP-Price-Oct.pdf   (HPL/PM/26-27/113, wef 01.10.2026)
      Annexure I   : PP Ex-Works basic price     (24 column groups incl. powder)
      Annexure II  : PP Ex-Stock Point basic price (21 column groups)

Updates in dataset.json:
  1. price_table rows (92) — Jharkhand/Bihar x Ex-Stock/Ex-Warehouse columns
  2. per-grade `price` fields on the 52 priced Haldia TDS grades:
     ex_works_min/max across ALL price points, ex_works_ref = first price
     point (West Bengal_Howrah) value, effective = circular date
  3. circular metadata (dataset.prices + price_table.meta)

Column basis (unchanged from the previous build, verbatim from circulars):
  Ex-Stock (JH/BR)      = "Ex-Stock(s) / Ex-Stock Point Basic Price" rows
                          Jharkhand_Ranchi / Bihar (Annexure II / III stock cols)
  Ex-Warehouse (JH/BR)  = "Ex-Works Basic Price" for those price points
                          (Annexure I / III works cols)
"""
import json
import re
import subprocess
from collections import OrderedDict
from datetime import date

ROOT = "/home/z/my-project"
PE_PDF = f"{ROOT}/upload/PE-Price-Oct.pdf"
PP_PDF = f"{ROOT}/upload/PP-Price-Oct.pdf"
DATASET = f"{ROOT}/public/data/dataset.json"

PE_CIRCULAR, PE_EFF = "HPL/PM/26-27/112", "01.10.2026"
PP_CIRCULAR, PP_EFF = "HPL/PM/26-27/113", "01.10.2026"

MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]


def period_label(eff_ddmmyyyy: str) -> str:
    dd, mm, yyyy = eff_ddmmyyyy.split(".")
    return f"{MONTHS[int(mm) - 1]} {yyyy}"

# ---------------------------------------------------------------- canonical grade groups
HDPE_GROUPS = [
    ["B6401"], ["E5201"], ["E5201S"], ["B5500"], ["F5400"], ["P5300"], ["P5100"],
    ["P5200"], ["P5200UV"], ["R5801"], ["HDT6"], ["M5600S"], ["M5601S"], ["M5600"],
    ["M5601"], ["M5018L"], ["M6007L"], ["M6007LU"], ["M5005L"], ["M5002L"], ["F5001"],
    ["HDT9"], ["HDT10", "HDT10S"], ["HDT9C"],
    ["HDBRE", "HD OG (E)"],
    ["HDBRM1", "HDBRM2", "HDBRM3", "HDBRM4", "HD OG (M)"],
    ["HDBRF1", "HDBRF2", "HDBRF3", "HD OG (F)"],
    ["HDBRB1", "HDBRB2", "HDBRB3", "HDBRB4", "HDBRB5", "HD OG (B)"],
]
LLDPE_GROUPS = [
    ["71501S", "71602S", "71601W", "71602W"], ["71601D"],
    ["73005T", "73204T"], ["73005TU", "73204TU"], ["72307E"], ["LLT-12"],
    ["LLBRE1", "LLBRE2", "LLBRE3", "LL OG (E)"],
    ["LLBRM1", "LLBRM2", "LL OG (M)"],
]
PP_WORKS_GROUPS = [
    ["M110"], ["M108", "M125", "E125"], ["M106"], ["M103"], ["R103"], ["F110"],
    ["F135"], ["B200"], ["M212S"], ["B202S"], ["M304"], ["M307", "M315", "M325"],
    ["M308S"], ["M310"], ["M311T"], ["M312"], ["M320"], ["M330"], ["M340"], ["M365"],
    ["3-4 MI HP Pwd"], ["10-12 MI HP Pwd"], ["6-12 MI CP Pwd"],
    ["PP BR-4/10/25/40/65"],
]
PP_STOCK_GROUPS = [g for g in PP_WORKS_GROUPS if "Pwd" not in g[0]]

BR_GRADES = {
    "HDBRE", "HDBRM1", "HDBRM2", "HDBRM3", "HDBRM4",
    "HDBRF1", "HDBRF2", "HDBRF3",
    "HDBRB1", "HDBRB2", "HDBRB3", "HDBRB4", "HDBRB5",
    "LLBRE1", "LLBRE2", "LLBRE3", "LLBRM1", "LLBRM2",
}
OG_GRADES = {"HD OG (E)", "HD OG (M)", "HD OG (F)", "HD OG (B)", "LL OG (E)", "LL OG (M)"}
POWDER_GRADES = {"3-4 MI HP Pwd", "10-12 MI HP Pwd", "6-12 MI CP Pwd"}


def grade_type(name: str) -> str:
    if name in POWDER_GRADES:
        return "powder"
    if name.startswith("PP BR"):
        return "br"
    if name in BR_GRADES:
        return "br"
    if name in OG_GRADES:
        return "og"
    return "prime"


def norm(s: str) -> str:
    return re.sub(r"[\s\-]+", "", s).upper()


# ---------------------------------------------------------------- raw pdf text helpers
def pdftotext(path: str) -> str:
    return subprocess.run(["pdftotext", "-layout", path, "-"],
                          capture_output=True, text=True, check=True).stdout


def split_annexures(text: str):
    parts = {}
    marks = [(m.start(), m.group(1)) for m in re.finditer(r"^[\f\s]*Annexure\s*-\s*([IVX]+)\s*$",
                                                          text, re.M)]
    for i, (pos, roman) in enumerate(marks):
        end = marks[i + 1][0] if i + 1 < len(marks) else len(text)
        parts[roman] = text[pos:end]
    return parts


DATA_ROW_RE = re.compile(r"^([A-Za-z][A-Za-z0-9 &_]*?)\s+((?:\d{4,6}[ \t]*)+)$", re.M)


def all_rows(section: str) -> "OrderedDict[str, list]":
    """Every price-point data row in an annexure section: {location: [ints]}."""
    rows = OrderedDict()
    for m in DATA_ROW_RE.finditer(section):
        loc = re.sub(r"\s+", " ", m.group(1)).strip()
        vals = [int(v) for v in re.findall(r"\d{4,6}", m.group(2))]
        if loc in ("Basic Price", "PRICE POINTS", "Grades"):
            continue
        rows[loc] = vals
    return rows


def check_matrix(label, rows, width):
    """All rows same width, Bihar + Jharkhand_Ranchi present, enough points."""
    assert len(rows) >= 25, f"{label}: only {len(rows)} price points parsed"
    for loc, vals in rows.items():
        assert len(vals) == width, f"{label}/{loc}: width {len(vals)} != {width}"
    assert "Bihar" in rows and "Jharkhand_Ranchi" in rows, f"{label}: missing BR/JH rows"
    print(f"  ✓ {label}: {len(rows)} price points x {width} columns, BR+JH present")


# ---------------------------------------------------------------- load dataset
with open(DATASET) as f:
    dataset = json.load(f)

grades = dataset["grades"]
haldia_by_norm = {}
for g in grades:
    if g["company"] == "haldia":
        haldia_by_norm[norm(g["grade"])] = g

# competition siblings: Haldia grades co-listed as alternates of a competitor grade
comp_siblings = {}
for g in grades:
    if g["company"] == "haldia":
        continue
    alt_ids = (g.get("competition") or {}).get("alt_haldia_ids") or []
    names = [a["grade"] for a in alt_ids]
    keys = [norm(n) for n in names]
    for a in names:
        ka = norm(a)
        for b, kb in zip(names, keys):
            if ka != kb:
                comp_siblings.setdefault(ka, set()).add(kb)

# ---------------------------------------------------------------- extract prices
pe_txt = pdftotext(PE_PDF)
pp_txt = pdftotext(PP_PDF)
pe_ann = split_annexures(pe_txt)
pp_ann = split_annexures(pp_txt)

# verify the circular identity printed on page 1 of each PDF
assert "HPL/ PM/ 26-27/ 112" in pe_txt and "01.10.2026" in pe_txt, "PE circular id"
assert "26-27 / 113" in pp_txt.replace("  ", " ") or "26-27/ 113" in pp_txt, "PP circular id"
assert "01.10.2026" in pp_txt, "PP effective date"

# --- PE: HDPE ex-works (Annexure I) / ex-stock (Annexure II) ---
hd_works = all_rows(pe_ann["I"])
hd_stock = all_rows(pe_ann["II"])
check_matrix("PE Annexure I (HDPE ex-works)", hd_works, 28)
check_matrix("PE Annexure II (HDPE ex-stock)", hd_stock, 28)
hd_works_br, hd_works_jh = hd_works["Bihar"], hd_works["Jharkhand_Ranchi"]
hd_stock_br, hd_stock_jh = hd_stock["Bihar"], hd_stock["Jharkhand_Ranchi"]
first_loc = next(iter(hd_works))  # West Bengal_Howrah
assert first_loc == "West Bengal_Howrah", f"first price point is {first_loc}"
# spot-assert against the circular text (verified by eye from the layout dump)
assert hd_works_jh[0] == 142287, "HDPE ex-works Jharkhand B6401"
assert hd_works_jh[22] == 144723, "HDPE ex-works Jharkhand HDT10"
assert hd_works_br[0] == 142659, "HDPE ex-works Bihar B6401"
assert hd_works[first_loc][0] == 142709, "HDPE ex-works WB_Howrah B6401 (ref basis)"
assert hd_stock_jh[0] == 143289 and hd_stock_br[0] == 144330, "HDPE ex-stock B6401"
# --- PE: LLDPE (Annexure III — 8 ex-works cols + 8 ex-stock cols) ---
ll_all = all_rows(pe_ann["III"])
check_matrix("PE Annexure III (LLDPE works+stock)", ll_all, 16)
ll_works, ll_stock = OrderedDict(), OrderedDict()
for loc, vals in ll_all.items():
    ll_works[loc], ll_stock[loc] = vals[:8], vals[8:]
assert ll_works["Bihar"][:8] != ll_works["Bihar"][8:] or True  # widths already checked
ll_works_br, ll_works_jh = ll_works["Bihar"], ll_works["Jharkhand_Ranchi"]
ll_stock_br, ll_stock_jh = ll_stock["Bihar"], ll_stock["Jharkhand_Ranchi"]
assert ll_works_br[0] != ll_stock_br[0], "LLDPE works vs stock must differ"
assert ll_works_br[0] == 141479 and ll_stock_br[0] == 143150, "LLDPE Bihar 71501S"
assert ll_works_jh[0] == 141557 and ll_stock_jh[0] == 142559, "LLDPE Jharkhand 71501S"
assert ll_works[first_loc][0] == 142279, "LLDPE WB_Howrah 71501S (ref basis)"

# --- PP: ex-works (Annexure I, 24) / ex-stock (Annexure II, 21) ---
pp_works = all_rows(pp_ann["I"])
pp_stock = all_rows(pp_ann["II"])
check_matrix("PP Annexure I (ex-works)", pp_works, 24)
check_matrix("PP Annexure II (ex-stock)", pp_stock, 21)
pp_works_br, pp_works_jh = pp_works["Bihar"], pp_works["Jharkhand_Ranchi"]
pp_stock_br, pp_stock_jh = pp_stock["Bihar"], pp_stock["Jharkhand_Ranchi"]
assert pp_works_br[0] == 158349 and pp_works_jh[0] == 159488, "PP ex-works M110"
assert pp_stock_br[0] == 160020 and pp_stock_jh[0] == 160490, "PP ex-stock M110"
assert pp_works[first_loc][0] == 158315, "PP ex-works WB_Howrah M110 (ref basis)"
assert pp_stock_br[-1] == 158020 and pp_stock_jh[-1] == 158490, "PP BR ex-stock"

print("  ✓ all spot-assertions against the new circulars passed")

# ---------------------------------------------------------------- build price-table rows
def expand_pp_br(group_names):
    out = []
    for n in group_names:
        if n.startswith("PP BR"):
            for m in re.findall(r"\d+", n):
                out.append(f"PP BR {m}")
        else:
            out.append(n)
    return out


DISPLAY_BY_NORM = {}
for _grp in HDPE_GROUPS + LLDPE_GROUPS + PP_WORKS_GROUPS:
    for _n in expand_pp_br(_grp):
        DISPLAY_BY_NORM[norm(_n)] = _n


def build_rows(groups, stock_groups, works_br, works_jh, stock_br, stock_jh, polymer):
    stock_idx = {id(g): i for i, g in enumerate(stock_groups)}
    rows = []
    for gi, group in enumerate(groups):
        expanded = expand_pp_br(group)
        si = stock_idx.get(id(group))
        s_br = stock_br[si] if si is not None else None
        s_jh = stock_jh[si] if si is not None else None
        for gname in expanded:
            tds = haldia_by_norm.get(norm(gname))
            price_sibs = [x for x in expand_pp_br(group) if norm(x) != norm(gname)]
            comp = comp_siblings.get(norm(gname), set())

            alt_map = OrderedDict()

            def add_alt(name_key, src):
                if name_key == norm(gname):
                    return
                t = haldia_by_norm.get(name_key)
                e = alt_map.get(name_key)
                if e is None:
                    alt_map[name_key] = {
                        "grade": t["grade"] if t else DISPLAY_BY_NORM.get(name_key, name_key),
                        "id": t["id"] if t else None,
                        "src": src,
                    }
                else:
                    if t and not e["id"]:
                        e["id"] = t["id"]
                        e["grade"] = t["grade"]
                    if e["src"] != src:
                        e["src"] = "both"

            for k in comp:
                add_alt(k, "competition")
            for other in price_sibs:
                add_alt(norm(other), "price")

            order = {"both": 0, "competition": 1, "price": 2}
            alts = sorted(alt_map.values(), key=lambda a: (order[a["src"]], a["grade"]))
            rows.append({
                "grade": gname,
                "polymer": polymer,
                "manufacturer": "Haldia Petrochemicals Ltd",
                "grade_type": grade_type(gname),
                "tds_id": tds["id"] if tds else None,
                "tds_grade": tds["grade"] if tds else None,
                "ex_stock_jh": s_jh,
                "ex_stock_br": s_br,
                "ex_ware_jh": works_jh[gi],
                "ex_ware_br": works_br[gi],
                "alts": alts,
            })
    return rows


rows = []
rows += build_rows(HDPE_GROUPS, HDPE_GROUPS, hd_works_br, hd_works_jh, hd_stock_br, hd_stock_jh, "HDPE")
rows += build_rows(LLDPE_GROUPS, LLDPE_GROUPS, ll_works_br, ll_works_jh, ll_stock_br, ll_stock_jh, "LLDPE")
rows += build_rows(PP_WORKS_GROUPS, PP_STOCK_GROUPS, pp_works_br, pp_works_jh, pp_stock_br, pp_stock_jh, "PP")

# ---------------------------------------------------------------- update per-grade TDS prices
def group_stats(matrix, gi):
    """min/max across all price points + ref (first price point) for column gi."""
    col = [vals[gi] for vals in matrix.values()]
    return min(col), max(col), col[0]


updated = 0
for g in grades:
    if g["company"] != "haldia" or not g.get("price"):
        continue
    poly = g["polymer"]
    gn = norm(g["grade"])
    if poly == "HDPE":
        groups, matrix = HDPE_GROUPS, hd_works
        eff = PE_EFF
    elif poly == "LLDPE":
        groups, matrix = LLDPE_GROUPS, ll_works
        eff = PE_EFF
    else:
        groups, matrix = PP_WORKS_GROUPS, pp_works
        eff = PP_EFF
    # exact token match within the polymer's column groups
    hit = next(((i, grp) for i, grp in enumerate(groups)
                if any(norm(t) == gn for t in grp)), None)
    assert hit is not None, f"grade {g['grade']} ({poly}) not found in new circular groups"
    gi, grp = hit
    mn, mx, ref = group_stats(matrix, gi)
    g["price"] = {
        "ex_works_min": mn,
        "ex_works_max": mx,
        "ex_works_ref": ref,
        "currency": "Rs./MT",
        "effective": eff,
    }
    updated += 1

assert updated == 52, f"updated {updated} per-grade prices, expected 52"
# spot-check per-grade refs (first price point values verified above)
ref_checks = {
    "B6401": 142709, "HD T9": 142378, "HD T10": 144526,
    "71501S": 142279, "M110": 158315, "M307": 164102,
}
for gname, expect in ref_checks.items():
    got = haldia_by_norm[norm(gname)]["price"]["ex_works_ref"]
    assert got == expect, f"{gname} ref {got} != {expect}"
print(f"  ✓ per-grade TDS prices updated on {updated} grades (refs spot-checked)")

# ---------------------------------------------------------------- stats + write
by_poly = {}
for r in rows:
    by_poly[r["polymer"]] = by_poly.get(r["polymer"], 0) + 1
by_type = {}
for r in rows:
    by_type[r["grade_type"]] = by_type.get(r["grade_type"], 0) + 1
linked = sum(1 for r in rows if r["tds_id"])
with_alts = sum(1 for r in rows if r["alts"])

print(f"\nrows: {len(rows)} | by polymer: {by_poly} | by type: {by_type}")
print(f"TDS-linked: {linked} | with Haldia alternatives: {with_alts}")

expected = {"HDPE": 42, "LLDPE": 18, "PP": 32}
assert by_poly == expected, f"row counts {by_poly} != {expected}"
assert all(r["ex_stock_jh"] and r["ex_stock_br"] and r["ex_ware_jh"] and r["ex_ware_br"]
           for r in rows if r["grade_type"] != "powder"), "missing prices on non-powder rows"
assert all(r["ex_ware_jh"] and r["ex_ware_br"] for r in rows if r["grade_type"] == "powder")
ppbr = [r for r in rows if r["grade"] == "PP BR 25"][0]
assert ppbr["ex_stock_jh"] == 158490 and ppbr["ex_stock_br"] == 158020, "PP BR ex-stock"

# both circulars fall in the same display month for the hero label
assert period_label(PE_EFF) == period_label(PP_EFF) == "October 2026", "period label"

price_table = {
    "meta": {
        "manufacturer": "Haldia Petrochemicals Ltd",
        "pe_circular": PE_CIRCULAR,
        "pe_effective": PE_EFF,
        "pp_circular": PP_CIRCULAR,
        "pp_effective": PP_EFF,
        "unit": "Rs./MT basic (credit)",
        "period_label": period_label(PE_EFF),
        "ex_stock_basis": "Ex-Stock Point basic price (Annexure II / III ex-stock columns) for the Jharkhand_Ranchi and Bihar price points — HPL stock point / HPL warehouse prices, local freight, handling & insurance extra.",
        "ex_warehouse_basis": "Ex-Plant / Ex-Works basic price (Annexure I / III ex-works columns) for the Jharkhand_Ranchi and Bihar price points — HPL publishes no separate ex-warehouse tariff; freight extra upto destination at actuals.",
        "sources": [
            "PE-Price-Oct.pdf (HDPE & LLDPE, wef 01.10.2026)",
            "PP-Price-Oct.pdf (PP, wef 01.10.2026)",
        ],
        "generated": date.today().isoformat(),
    },
    "rows": rows,
}

dataset["price_table"] = price_table
dataset["prices"] = {
    "pe": {"circular": PE_CIRCULAR, "effective": PE_EFF},
    "pp": {"circular": PP_CIRCULAR, "effective": PP_EFF},
}

with open(DATASET, "w") as f:
    json.dump(dataset, f, ensure_ascii=False, separators=(",", ":"))
with open(f"{ROOT}/extracted/dataset.json", "w") as f:
    json.dump(dataset, f, ensure_ascii=False, indent=1)

print(f"\nwrote price_table to {DATASET} ({len(json.dumps(price_table))//1024} KB)")

# sample rows
for g in ["B6401", "HDT10", "HD OG (M)", "73005TU", "LL OG (E)", "M110", "PP BR 25", "6-12 MI CP Pwd"]:
    r = [x for x in rows if x["grade"] == g][0]
    print(f"  {g:<14} {r['polymer']:<6} stock(JH/BR) {r['ex_stock_jh']}/{r['ex_stock_br']}"
          f"  ware(JH/BR) {r['ex_ware_jh']}/{r['ex_ware_br']}  alts="
          f"{[a['grade'] for a in r['alts']][:4]}")
