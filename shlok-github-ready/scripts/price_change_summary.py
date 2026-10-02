#!/usr/bin/env python3
"""Summarize price changes between the previous circular (in git HEAD dataset)
and the new October dataset: per-polymer min/max/median delta across the
Jharkhand/Bihar x Ex-Stock/Ex-Warehouse columns."""
import json
import subprocess

ROOT = "/home/z/my-project"

old_raw = subprocess.run(
    ["git", "-C", ROOT, "show", "HEAD:public/data/dataset.json"],
    capture_output=True, text=True, check=True).stdout
old = {r["grade"]: r for r in json.loads(old_raw)["price_table"]["rows"]}
new = {r["grade"]: r for r in json.load(open(f"{ROOT}/public/data/dataset.json"))["price_table"]["rows"]}

cols = ["ex_stock_jh", "ex_stock_br", "ex_ware_jh", "ex_ware_br"]
by_poly = {}
n_changed = n_same = 0
examples = []
for g, nr in new.items():
    orow = old.get(g)
    if not orow:
        continue
    for c in cols:
        ov, nv = orow.get(c), nr.get(c)
        if ov is None or nv is None:
            continue
        d = nv - ov
        by_poly.setdefault(nr["polymer"], []).append(d)
        if d != 0:
            n_changed += 1
            if len(examples) < 12:
                examples.append((g, nr["polymer"], c, ov, nv, d))
        else:
            n_same += 1

print(f"changed cells: {n_changed} | unchanged cells: {n_same}")
for poly, ds in sorted(by_poly.items()):
    ds.sort()
    print(f"  {poly:<6} deltas: min {ds[0]:+6d} · median {ds[len(ds)//2]:+6d} · max {ds[-1]:+6d}  ({len(ds)} cells)")
print("\nsample changes:")
for g, poly, c, ov, nv, d in examples:
    print(f"  {g:<14} {poly:<6} {c:<12} {ov} -> {nv}  ({d:+d})")
