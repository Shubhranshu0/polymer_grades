#!/usr/bin/env python3
"""Build the consolidated Haldia price table for the Pricing page.

Sources (the ONLY price sources — HPL September 2026 circulars):
  - upload/Polyethylene Price-September Price.pdf  (HPL/PM/26-27/101, wef 07.09.2026)
      Annexure I   : HDPE Ex-Works basic price  (price points x grade columns)
      Annexure II  : HDPE Ex-Stock basic price
      Annexure III : LLDPE combined table (Ex-Works + Ex-Stock Point column groups)
  - upload/Polypropylene Price-September Month.pdf (HPL/PM/26-27/100, wef 05.09.2026)
      Annexure I   : PP Ex-Works basic price (24 grade columns, incl. 3 powder grades)
      Annexure II  : PP Ex-Stock Point basic price (21 grade columns)

Output rows carry, per Haldia grade (every grade named in the price lists):
  grade | polymer | manufacturer | ex_stock_jh | ex_stock_br | ex_ware_jh | ex_ware_br | alts

Column basis (all values verbatim from the circulars):
  Ex-Stock Price (Jharkhand/Bihar)  = "Ex-Stock Point Basic Price" (Annexure II / III
                                      ex-stock column group) for rows Jharkhand_Ranchi / Bihar
  Ex-Warehouse Price (Jharkhand/Bihar) = "Ex-Works Basic Price" (Annexure I / III ex-works
                                      column group) for rows Jharkhand_Ranchi / Bihar
  (HPL terms treat ex-stock / HPL-warehouse alike and publish no separate ex-warehouse
   tariff — both published bases are shown; footnoted in the UI.)

Verification: every extracted value is asserted against dataset.json (previous verified
parse) AND the raw pdftotext rows; the HDPE ex-works Jharkhand_Ranchi row (dropped by the
old multi-page parser) is recovered from the raw text and asserted against column count.
"""
import json
import re
import subprocess
from collections import OrderedDict
from datetime import date

ROOT = "/home/z/my-project"
PE_PDF = f"{ROOT}/upload/Polyethylene Price-September Price.pdf"
PP_PDF = f"{ROOT}/upload/Polypropylene Price-September Month.pdf"
DATASET = f"{ROOT}/public/data/dataset.json"

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
    """Split raw text into {roman: section_text} on 'Annexure - X' markers."""
    parts = {}
    marks = [(m.start(), m.group(1)) for m in re.finditer(r"^[\f\s]*Annexure\s*-\s*([IVX]+)\s*$",
                                                          text, re.M)]
    for i, (pos, roman) in enumerate(marks):
        end = marks[i + 1][0] if i + 1 < len(marks) else len(text)
        parts[roman] = text[pos:end]
    return parts


def find_row(section: str, location: str):
    """Return the list of numeric values on the `location` price-point row."""
    m = re.search(rf"^\s*{re.escape(location)}\s+((?:\d{{4,6}}\s*)+)$",
                  section, re.M)
    if not m:
        return None
    return [int(v) for v in re.findall(r"\d{4,6}", m.group(1))]


# ---------------------------------------------------------------- load dataset
with open(DATASET) as f:
    dataset = json.load(f)

grades = dataset["grades"]
haldia_by_norm = {}
for g in grades:
    if g["company"] == "haldia":
        haldia_by_norm[norm(g["grade"])] = g

# competition siblings: Haldia grades co-listed as alternates of a competitor grade
comp_siblings = {}  # norm(haldia grade) -> set of norm(other haldia grades)
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

# --- PE: HDPE ex-works (Annexure I) / ex-stock (Annexure II) ---
hd_works_br = find_row(pe_ann["I"], "Bihar")
hd_works_jh = find_row(pe_ann["I"], "Jharkhand_Ranchi")
hd_stock_br = find_row(pe_ann["II"], "Bihar")
hd_stock_jh = find_row(pe_ann["II"], "Jharkhand_Ranchi")
assert len(hd_works_br) == 28 and len(hd_works_jh) == 28, "HDPE ex-works row width"
assert len(hd_stock_br) == 28 and len(hd_stock_jh) == 28, "HDPE ex-stock row width"
# spot-assert against the circular text (checked by eye from the PDF layout dump)
assert hd_works_jh[0] == 140287, "HDT/HDPE ex-works Jharkhand B6401"
assert hd_works_jh[22] == 142723, "HDPE ex-works Jharkhand HDT10"
assert hd_works_br[0] == 140659, "HDPE ex-works Bihar B6401"
assert hd_stock_jh[0] == 141289 and hd_stock_br[0] == 142330

# --- PE: LLDPE (Annexure III — 8 ex-works cols + 8 ex-stock cols) ---
ll_works_br = find_row(pe_ann["III"], "Bihar")
ll_works_jh = find_row(pe_ann["III"], "Jharkhand_Ranchi")
assert len(ll_works_br) == 16 and len(ll_works_jh) == 16, "LLDPE row width"
assert ll_works_br[:8] != ll_works_br[8:], "LLDPE works vs stock must differ"
ll_stock_br, ll_stock_jh = ll_works_br[8:], ll_works_jh[8:]
ll_works_br, ll_works_jh = ll_works_br[:8], ll_works_jh[:8]

# --- PP: ex-works (Annexure I, 24) / ex-stock (Annexure II, 21) ---
pp_works_br = find_row(pp_ann["I"], "Bihar")
pp_works_jh = find_row(pp_ann["I"], "Jharkhand_Ranchi")
pp_stock_br = find_row(pp_ann["II"], "Bihar")
pp_stock_jh = find_row(pp_ann["II"], "Jharkhand_Ranchi")
assert len(pp_works_br) == 24 and len(pp_works_jh) == 24, "PP ex-works row width"
assert len(pp_stock_br) == 21 and len(pp_stock_jh) == 21, "PP ex-stock row width"
assert pp_works_br[0] == 150849 and pp_works_jh[0] == 151988, "PP ex-works M110"
assert pp_stock_br[0] == 152520 and pp_stock_jh[0] == 152990, "PP ex-stock M110"

# ---------------------------------------------------------------- cross-verify vs dataset
def dataset_row(doc, poly, basis, location):
    sec = dataset["prices"][doc][poly][basis]
    for r in sec["matrix"]:
        if r["location"] == location:
            return [int(r["prices"][c[0]]) for c in sec["columns"]]
    return None


def crosscheck(label, raw, ds):
    if ds is None:
        print(f"  · {label}: not in dataset (recovered from raw text) — OK")
        return
    assert raw == ds, f"{label} mismatch:\n raw={raw}\n ds ={ds}"
    print(f"  ✓ {label}: {len(raw)} values match dataset")


crosscheck("HDPE ex-works Bihar", hd_works_br, dataset_row("pe", "HDPE", "ex_works", "Bihar"))
crosscheck("HDPE ex-stock Bihar", hd_stock_br, dataset_row("pe", "HDPE", "ex_stock", "Bihar"))
crosscheck("HDPE ex-stock Jharkhand", hd_stock_jh, dataset_row("pe", "HDPE", "ex_stock", "Jharkhand_Ranchi"))
print("  · HDPE ex-works Jharkhand: recovered from raw text (was dropped by old parser) — OK")
crosscheck("LLDPE ex-works Bihar", ll_works_br, dataset_row("pe", "LLDPE", "ex_works", "Bihar"))
crosscheck("LLDPE ex-stock Bihar", ll_stock_br, dataset_row("pe", "LLDPE", "ex_stock", "Bihar"))
crosscheck("LLDPE ex-works Jharkhand", ll_works_jh, dataset_row("pe", "LLDPE", "ex_works", "Jharkhand_Ranchi"))
crosscheck("LLDPE ex-stock Jharkhand", ll_stock_jh, dataset_row("pe", "LLDPE", "ex_stock", "Jharkhand_Ranchi"))
crosscheck("PP ex-works Bihar", pp_works_br, dataset_row("pp", "PP", "ex_works", "Bihar"))
crosscheck("PP ex-works Jharkhand", pp_works_jh, dataset_row("pp", "PP", "ex_works", "Jharkhand_Ranchi"))
crosscheck("PP ex-stock Bihar", pp_stock_br, dataset_row("pp", "PP", "ex_stock", "Bihar"))
crosscheck("PP ex-stock Jharkhand", pp_stock_jh, dataset_row("pp", "PP", "ex_stock", "Jharkhand_Ranchi"))

# ---------------------------------------------------------------- build rows
def expand_pp_br(group_names):
    """'PP BR-4/10/25/40/65' -> PP BR 4 / PP BR 10 / PP BR 25 / PP BR 40 / PP BR 65."""
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
    """stock_groups: the grade-group list of the ex-stock annexure (groups absent there
    get None — e.g. PP powder grades are ex-works only). Group lists are matched by
    identity because PP ex-stock omits the 3 powder groups."""
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

            # merge alternatives by normalized name; prefer TDS display names
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
# PP BR carries a real ex-stock value (present in the ex-stock annexure)
ppbr = [r for r in rows if r["grade"] == "PP BR 25"][0]
assert ppbr["ex_stock_jh"] == 150990 and ppbr["ex_stock_br"] == 150520, "PP BR ex-stock"

price_table = {
    "meta": {
        "manufacturer": "Haldia Petrochemicals Ltd",
        "pe_circular": "HPL/PM/26-27/101",
        "pe_effective": "07.09.2026",
        "pp_circular": "HPL/PM/26-27/100",
        "pp_effective": "05.09.2026",
        "unit": "Rs./MT basic (credit)",
        "ex_stock_basis": "Ex-Stock Point basic price (Annexure II / III ex-stock columns) for the Jharkhand_Ranchi and Bihar price points — HPL stock point / HPL warehouse prices, local freight, handling & insurance extra.",
        "ex_warehouse_basis": "Ex-Plant / Ex-Works basic price (Annexure I / III ex-works columns) for the Jharkhand_Ranchi and Bihar price points — HPL publishes no separate ex-warehouse tariff; freight extra upto destination at actuals.",
        "sources": [
            "Polyethylene Price-September Price.pdf (HDPE & LLDPE, wef 07.09.2026)",
            "Polypropylene Price-September Month.pdf (PP, wef 05.09.2026)",
        ],
        "generated": date.today().isoformat(),
    },
    "rows": rows,
}

dataset["price_table"] = price_table
# the all-India price matrices are no longer rendered — keep only circular metadata
dataset["prices"] = {
    "pe": {"circular": "HPL/PM/26-27/101", "effective": "07.09.2026"},
    "pp": {"circular": "HPL/PM/26-27/100", "effective": "05.09.2026"},
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
          f"{[a['grade'] for a in r['alts']]}")
