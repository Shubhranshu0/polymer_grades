#!/usr/bin/env python3
"""Final audit: independently re-parse the HPL circular rows and check EVERY
price_table value in the deployed dataset.json against the raw PDF text.
Updated for the current circulars: PE-Price-Oct.pdf (HPL/PM/26-27/112,
wef 01.10.2026) and PP-Price-Oct.pdf (HPL/PM/26-27/113, wef 01.10.2026).
Also audits the per-grade TDS price fields (min/max/ref over the full all-India
matrix, ref = first price point West Bengal_Howrah)."""
import json
import re
import subprocess

ROOT = "/home/z/my-project"


def pdftotext(path):
    return subprocess.run(["pdftotext", "-layout", path, "-"],
                          capture_output=True, text=True, check=True).stdout


def annexures(text):
    parts = {}
    marks = [(m.start(), m.group(1)) for m in
             re.finditer(r"^[\f\s]*Annexure\s*-\s*([IVX]+)\s*$", text, re.M)]
    for i, (pos, roman) in enumerate(marks):
        end = marks[i + 1][0] if i + 1 < len(marks) else len(text)
        parts[roman] = text[pos:end]
    return parts


def row(sec, loc):
    m = re.search(rf"^\s*{loc}\s+((?:\d{{4,6}}\s*)+)$", sec, re.M)
    return [int(v) for v in re.findall(r"\d{4,6}", m.group(1))]


pe = annexures(pdftotext(f"{ROOT}/upload/PE-Price-Oct.pdf"))
pp = annexures(pdftotext(f"{ROOT}/upload/PP-Price-Oct.pdf"))

# section -> (works_br, works_jh, stock_br, stock_jh)
sections = {
    "HDPE": (row(pe["I"], "Bihar"), row(pe["I"], "Jharkhand_Ranchi"),
             row(pe["II"], "Bihar"), row(pe["II"], "Jharkhand_Ranchi")),
    "LLDPE": (row(pe["III"], "Bihar")[:8], row(pe["III"], "Jharkhand_Ranchi")[:8],
              row(pe["III"], "Bihar")[8:], row(pe["III"], "Jharkhand_Ranchi")[8:]),
    "PP": (row(pp["I"], "Bihar"), row(pp["I"], "Jharkhand_Ranchi"),
           row(pp["II"], "Bihar"), row(pp["II"], "Jharkhand_Ranchi")),
}

# column-group index per grade (must mirror the circular headers, verified earlier)
GROUPS = {
    "HDPE": [
        "B6401", "E5201", "E5201S", "B5500", "F5400", "P5300", "P5100", "P5200",
        "P5200UV", "R5801", "HDT6", "M5600S", "M5601S", "M5600", "M5601", "M5018L",
        "M6007L", "M6007LU", "M5005L", "M5002L", "F5001", "HDT9", "HDT10*", "HDT9C",
        "HDBRE*", "HDBRM*", "HDBRF*", "HDBRB*",
    ],
    "LLDPE": [
        "71501S*", "71601D", "73005T*", "73005TU*", "72307E", "LLT-12",
        "LLBRE1*", "LLBRM1*",
    ],
    "PP": [
        "M110", "M108*", "M106", "M103", "R103", "F110", "F135", "B200", "M212S",
        "B202S", "M304", "M307*", "M308S", "M310", "M311T", "M312", "M320", "M330",
        "M340", "M365", "3-4 MI HP Pwd", "10-12 MI HP Pwd", "6-12 MI CP Pwd", "PPBR*",
    ],
}
GROUP_MEMBERS = {
    "HDPE": {
        "HDT10*": ["HDT10", "HDT10S"],
        "HDBRE*": ["HDBRE", "HD OG (E)"],
        "HDBRM*": ["HDBRM1", "HDBRM2", "HDBRM3", "HDBRM4", "HD OG (M)"],
        "HDBRF*": ["HDBRF1", "HDBRF2", "HDBRF3", "HD OG (F)"],
        "HDBRB*": ["HDBRB1", "HDBRB2", "HDBRB3", "HDBRB4", "HDBRB5", "HD OG (B)"],
    },
    "LLDPE": {
        "71501S*": ["71501S", "71602S", "71601W", "71602W"],
        "73005T*": ["73005T", "73204T"],
        "73005TU*": ["73005TU", "73204TU"],
        "LLBRE1*": ["LLBRE1", "LLBRE2", "LLBRE3", "LL OG (E)"],
        "LLBRM1*": ["LLBRM1", "LLBRM2", "LL OG (M)"],
    },
    "PP": {
        "M108*": ["M108", "M125", "E125"],
        "M307*": ["M307", "M315", "M325"],
        "PPBR*": ["PP BR 4", "PP BR 10", "PP BR 25", "PP BR 40", "PP BR 65"],
    },
}

# expected value per (grade, basis)
expected = {}
for poly, groups in GROUPS.items():
    wbr, wjh, sbr, sjh = sections[poly]
    for gi, g in enumerate(groups):
        members = GROUP_MEMBERS.get(poly, {}).get(g, [g])
        # works column index -> ex-stock column index
        # HDPE/LLDPE: identical group lists; PP ex-stock omits the 3 powder groups
        if poly == "PP":
            if gi <= 19:
                stock_gi = gi
            elif g == "PPBR*":
                stock_gi = 20
            else:
                stock_gi = None
        else:
            stock_gi = gi
        for m in members:
            expected[(m, "ware_br")] = wbr[gi]
            expected[(m, "ware_jh")] = wjh[gi]
            expected[(m, "stock_br")] = sbr[stock_gi] if stock_gi is not None else None
            expected[(m, "stock_jh")] = sjh[stock_gi] if stock_gi is not None else None

ds = json.load(open(f"{ROOT}/public/data/dataset.json"))
rows = ds["price_table"]["rows"]
print(f"auditing {len(rows)} rows against raw circular text…")

errors = 0
seen = set()
for r in rows:
    key = r["grade"]
    seen.add(key)
    checks = [
        (r["ex_stock_jh"], expected.get((key, "stock_jh")), f"{key} stock JH"),
        (r["ex_stock_br"], expected.get((key, "stock_br")), f"{key} stock BR"),
        (r["ex_ware_jh"], expected.get((key, "ware_jh")), f"{key} ware JH"),
        (r["ex_ware_br"], expected.get((key, "ware_br")), f"{key} ware BR"),
    ]
    for got, want, label in checks:
        if got != want:
            print(f"  MISMATCH {label}: table={got} circular={want}")
            errors += 1

missing = {g for g, _ in expected} - seen
for m in sorted(missing):
    print(f"  MISSING from table: {m}")
    errors += 1
extra = seen - {g for g, _ in expected}
if extra:
    print(f"  EXTRA grades in table: {extra}")
    errors += 1

print(f"\n{len(rows)} rows · {4 * len(rows)} price cells · {errors} errors")

# ---------------------------------------------------------------- per-grade audit
DATA_ROW_RE = re.compile(r"^([A-Za-z][A-Za-z0-9 &_]*?)\s+((?:\d{4,6}[ \t]*)+)$", re.M)


def all_rows(section):
    from collections import OrderedDict
    out = OrderedDict()
    for m in DATA_ROW_RE.finditer(section):
        loc = re.sub(r"\s+", " ", m.group(1)).strip()
        out[loc] = [int(v) for v in re.findall(r"\d{4,6}", m.group(2))]
    return out


hd_w = all_rows(pe["I"])
ll_raw = all_rows(pe["III"])
pp_w = all_rows(pp["I"])
first_loc = next(iter(hd_w))
assert first_loc == "West Bengal_Howrah"


def norm(s):
    return re.sub(r"[\s\-]+", "", s).upper()


AUD_GROUPS = {
    "HDPE": [["B6401"], ["E5201"], ["E5201S"], ["B5500"], ["F5400"], ["P5300"], ["P5100"],
             ["P5200"], ["P5200UV"], ["R5801"], ["HDT6"], ["M5600S"], ["M5601S"], ["M5600"],
             ["M5601"], ["M5018L"], ["M6007L"], ["M6007LU"], ["M5005L"], ["M5002L"], ["F5001"],
             ["HDT9"], ["HDT10", "HDT10S"], ["HDT9C"], ["HDBRE", "HD OG (E)"],
             ["HDBRM1", "HDBRM2", "HDBRM3", "HDBRM4", "HD OG (M)"],
             ["HDBRF1", "HDBRF2", "HDBRF3", "HD OG (F)"],
             ["HDBRB1", "HDBRB2", "HDBRB3", "HDBRB4", "HDBRB5", "HD OG (B)"]],
    "LLDPE": [["71501S", "71602S", "71601W", "71602W"], ["71601D"],
              ["73005T", "73204T"], ["73005TU", "73204TU"], ["72307E"], ["LLT-12"],
              ["LLBRE1", "LLBRE2", "LLBRE3", "LL OG (E)"],
              ["LLBRM1", "LLBRM2", "LL OG (M)"]],
    "PP": [["M110"], ["M108", "M125", "E125"], ["M106"], ["M103"], ["R103"], ["F110"],
           ["F135"], ["B200"], ["M212S"], ["B202S"], ["M304"], ["M307", "M315", "M325"],
           ["M308S"], ["M310"], ["M311T"], ["M312"], ["M320"], ["M330"], ["M340"], ["M365"],
           ["3-4 MI HP Pwd"], ["10-12 MI HP Pwd"], ["6-12 MI CP Pwd"],
           ["PP BR-4/10/25/40/65"]],
}

gerrors = 0
checked = 0
for g in ds["grades"]:
    if g.get("company") != "haldia" or not g.get("price"):
        continue
    poly = g["polymer"]
    if poly == "HDPE":
        groups, matrix = AUD_GROUPS["HDPE"], hd_w
    elif poly == "LLDPE":
        groups, matrix = AUD_GROUPS["LLDPE"], {loc: v[:8] for loc, v in ll_raw.items()}
    else:
        groups, matrix = AUD_GROUPS["PP"], pp_w
    gn = norm(g["grade"])
    hit = next(((i, grp) for i, grp in enumerate(groups)
                if any(norm(t) == gn for t in grp)), None)
    assert hit, f"audit: {g['grade']} not in circular groups"
    gi, grp = hit
    col = [vals[gi] for vals in matrix.values()]
    want = {"ex_works_min": min(col), "ex_works_max": max(col), "ex_works_ref": col[0]}
    for k, v in want.items():
        checked += 1
        if g["price"][k] != v:
            print(f"  GRADE MISMATCH {g['grade']} {k}: dataset={g['price'][k]} circular={v}")
            gerrors += 1
    # effective date per polymer
    eff = "01.10.2026" if poly in ("HDPE", "LLDPE") else "01.10.2026"
    if g["price"].get("effective") != eff:
        print(f"  GRADE MISMATCH {g['grade']} effective: {g['price'].get('effective')} != {eff}")
        gerrors += 1

npriced = sum(1 for g in ds["grades"] if g.get("company") == "haldia" and g.get("price"))
print(f"per-grade TDS prices: {npriced} grades · {checked} values · {gerrors} errors")

total = errors + gerrors
print("ALL VALUES VERIFIED AGAINST THE ATTACHED PRICE LISTS" if total == 0 else "AUDIT FAILED")
