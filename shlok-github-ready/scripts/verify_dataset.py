#!/usr/bin/env python3
"""Final verification: complete grade coverage + competition mapping integrity."""
import json

BASE = "/home/z/my-project"
with open(f"{BASE}/public/data/dataset.json") as f:
    ds = json.load(f)
with open(f"{BASE}/extracted/competition.json") as f:
    comp = json.load(f)

grades = ds["grades"]
by_key = {(g["company"], g["grade"].upper()): g for g in grades}

errors, warnings = [], []

# ---- 1. company/polymer counts ----
from collections import Counter
cnt = Counter()
for g in grades:
    cnt[(g["company"], "PP" if g["polymer"].startswith("PP") else g["polymer"])] += 1

EXPECT = {
    ("haldia", "HDPE"): 24, ("haldia", "LLDPE"): 10, ("haldia", "PP"): 22,
    ("reliance", "HDPE"): 20, ("reliance", "LLDPE"): 22, ("reliance", "LDPE"): 15, ("reliance", "PP"): 47,
    ("ongc", "HDPE"): 13, ("ongc", "LLDPE"): 9, ("ongc", "PP"): 6,
    ("iocl", "HDPE"): 15, ("iocl", "LLDPE"): 9, ("iocl", "PP"): 41,  # user's stated minimums
}
for k, v in EXPECT.items():
    actual = cnt.get(k, 0)
    mark = "OK " if actual >= v else "FAIL"
    note = "" if actual == v else f" (user said {v}, documents contain {actual})"
    print(f"[{mark}] {k[0]:9s} {k[1]:6s} = {actual}{note}")
    if actual < v:
        errors.append(f"{k} has {actual} < required {v}")

print(f"\nTotal grades: {len(grades)}")

# ---- 2. every competition Excel row has a grade entry ----
SHEET_TO_CO = {"IOCL": "iocl", "RELIANCE-": "reliance", "ONGC": "ongc"}
for sheet, co in SHEET_TO_CO.items():
    rows = comp[sheet]["rows"]
    for r in rows:
        if not r or len(r) < 3 or not r[2]:
            continue
        grade_name = r[2].upper()
        g = by_key.get((co, grade_name))
        if not g:
            errors.append(f"Excel {sheet} row {r[2]} has NO grade entry on site")
        elif not g.get("competition"):
            errors.append(f"{co} {r[2]} has no competition info")
        elif not g["competition"].get("alt_haldia_ids") and g["competition"].get("alt_match_kind") not in ("none",):
            errors.append(f"{co} {r[2]} alt text present but no resolvable links: {g['competition']['haldia_alt'][:60]}")
    print(f"[OK ] Excel sheet {sheet:10s}: {len([r for r in rows if r and len(r)>2 and r[2]])} rows all mapped")

# ---- 3. reverse map integrity ----
grade_ids = {x["id"]: x for x in grades}
for g in grades:
    if g["company"] == "haldia":
        for c in g.get("competed_by", []):
            target = grade_ids.get(c["id"])
            if target is None:
                errors.append(f"{g['grade']} competed_by dangling id {c['id']}")
            elif target["company"] != c["company"] or target["grade"].upper() != c["grade"].upper():
                errors.append(f"{g['grade']} competed_by stale ref {c['grade']} -> {target['grade']}")
    else:
        c = g.get("competition", {})
        for ref in c.get("alt_haldia_ids", []) + c.get("alt_haldia_secondary", []):
            target = grade_ids.get(ref["id"])
            if target is None:
                errors.append(f"{g['grade']} alt_haldia dangling id {ref['id']}")
            elif target["company"] != "haldia" or target["grade"].upper() != ref["grade"].upper():
                errors.append(f"{g['grade']} alt points at wrong grade {ref['grade']}")

# ---- 4. every grade has core TDS data ----
weak = [g["grade"] for g in grades if len([p for p in g["props"] if p.get("value")]) < 3]
if weak:
    warnings.append(f"Grades with <3 props: {weak}")

# ---- 5. IOCL P-series present ----
pgrades = [g["grade"] for g in grades if g["company"] == "iocl" and g["grade"].startswith("P") and len(g["grade"]) > 6]
print(f"\nIOCL P-series grades present: {len(pgrades)} -> {pgrades}")

print("\n" + "=" * 60)
if errors:
    print(f"ERRORS ({len(errors)}):")
    for e in errors:
        print("  ✗", e)
else:
    print("ALL CHECKS PASSED — no missing grades, all Excel rows mapped.")
if warnings:
    print(f"Warnings: {warnings}")
