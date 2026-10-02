"use client";

import { useMemo, useState } from "react";
import { PriceTable, PriceTableRow, POLYMER_COLORS } from "@/lib/polymer-types";

type PolyKey = "all" | "HDPE" | "LLDPE" | "PP";
type TypeKey = "all" | "prime" | "br" | "og" | "powder";
type SortKey =
  | "grade"
  | "polymer"
  | "manufacturer"
  | "ex_stock_jh"
  | "ex_stock_br"
  | "ex_ware_jh"
  | "ex_ware_br"
  | "alts";

const POLY_ORDER = ["HDPE", "LLDPE", "PP"];
const TYPE_BADGE: Record<string, { label: string; cls: string }> = {
  br: { label: "BR", cls: "border-amber-300 bg-amber-50 text-amber-800" },
  og: { label: "OG", cls: "border-stone-300 bg-stone-100 text-stone-600" },
  powder: { label: "Powder", cls: "border-violet-300 bg-violet-50 text-violet-800" },
};

const COLUMNS: { key: SortKey; label: string; numeric?: boolean; group: "stock" | "ware" | "" }[] = [
  { key: "grade", label: "Grade", group: "" },
  { key: "polymer", label: "Polymer Type", group: "" },
  { key: "manufacturer", label: "Manufacturer", group: "" },
  { key: "ex_stock_jh", label: "Ex-Stock Price (Jharkhand)", numeric: true, group: "stock" },
  { key: "ex_stock_br", label: "Ex-Stock Price (Bihar)", numeric: true, group: "stock" },
  { key: "ex_ware_jh", label: "Ex-Warehouse Price (Jharkhand)", numeric: true, group: "ware" },
  { key: "ex_ware_br", label: "Ex-Warehouse Price (Bihar)", numeric: true, group: "ware" },
  { key: "alts", label: "Haldia Alternative", group: "" },
];

function inr(v: number | null) {
  if (v == null) return <span className="text-stone-300">—</span>;
  return <span>{v.toLocaleString("en-IN")}</span>;
}

export function PricesView({ table, onOpenGrade }: { table: PriceTable; onOpenGrade: (id: string) => void }) {
  const [poly, setPoly] = useState<PolyKey>("all");
  const [gtype, setGtype] = useState<TypeKey>("all");
  const [q, setQ] = useState("");
  const [sortKey, setSortKey] = useState<SortKey | null>(null);
  const [dir, setDir] = useState<1 | -1>(1);

  const meta = table.meta;

  const rows = useMemo(() => {
    const query = q.trim().toLowerCase();
    let out = table.rows.filter((r) => {
      if (poly !== "all" && r.polymer !== poly) return false;
      if (gtype !== "all" && r.grade_type !== gtype) return false;
      if (query) {
        const hay = [r.grade, r.tds_grade ?? "", r.polymer, ...r.alts.map((a) => a.grade)]
          .join(" ")
          .toLowerCase();
        if (!hay.includes(query)) return false;
      }
      return true;
    });
    if (sortKey) {
      const val = (r: PriceTableRow): string | number | null => {
        switch (sortKey) {
          case "grade":
            return r.grade.toLowerCase();
          case "polymer":
            return POLY_ORDER.indexOf(r.polymer);
          case "manufacturer":
            return r.manufacturer;
          case "alts":
            return r.alts.length ? r.alts[0].grade.toLowerCase() : "zzz";
          default:
            return r[sortKey] ?? null;
        }
      };
      out = [...out].sort((a, b) => {
        const va = val(a);
        const vb = val(b);
        // nulls (unpublished prices) always last
        if (va == null && vb == null) return 0;
        if (va == null) return 1;
        if (vb == null) return -1;
        if (va < vb) return -dir;
        if (va > vb) return dir;
        return POLY_ORDER.indexOf(a.polymer) - POLY_ORDER.indexOf(b.polymer) || a.grade.localeCompare(b.grade);
      });
    }
    return out;
  }, [table.rows, poly, gtype, q, sortKey, dir]);

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) {
      setDir((d) => (d === 1 ? -1 : 1));
    } else {
      setSortKey(key);
      setDir(1);
    }
  };

  const countBy = (p: PolyKey) => table.rows.filter((r) => p === "all" || r.polymer === p).length;

  return (
    <div>
      {/* ============ page header ============ */}
      <div className="mb-5">
        <div className="text-[10px] font-bold tracking-[0.3em] text-[#EA0C2F] uppercase">
          Haldia price list · Jharkhand &amp; Bihar · {meta.period_label}
        </div>
        <h2 className="mt-1.5 font-serif text-2xl font-bold tracking-tight text-stone-900 sm:text-3xl">
          Haldia grades — consolidated price table
        </h2>
        <p className="mt-2 max-w-3xl text-[13px] leading-relaxed text-stone-600">
          Every grade published in the HPL {meta.period_label} price circulars — <b>Halene</b> HDPE, LLDPE and PP
          including blending resin (BR), off-grade (OG) and powder grades — with ex-stock and ex-warehouse
          basic prices for the <b>Jharkhand</b> and <b>Bihar</b> price points. All values are taken verbatim
          from the attached price lists only; no other producer is included.
        </p>
        <div className="mt-3 flex flex-wrap gap-x-5 gap-y-1 font-mono text-[11px] text-stone-500">
          <span>
            PE circular <b className="text-stone-700">{meta.pe_circular}</b> · wef{" "}
            <b className="text-stone-700">{meta.pe_effective}</b>
          </span>
          <span>
            PP circular <b className="text-stone-700">{meta.pp_circular}</b> · wef{" "}
            <b className="text-stone-700">{meta.pp_effective}</b>
          </span>
          <span>
            Unit <b className="text-stone-700">{meta.unit}</b> · GST extra
          </span>
        </div>
      </div>

      {/* ============ controls ============ */}
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <div className="flex border border-stone-300">
          {(["all", "HDPE", "LLDPE", "PP"] as PolyKey[]).map((k) => (
            <button
              key={k}
              onClick={() => setPoly(k)}
              className={`px-3.5 py-2 text-[11px] font-bold tracking-widest uppercase transition-colors ${
                poly === k ? "bg-stone-900 text-white" : "bg-white text-stone-600 hover:bg-stone-100"
              }`}
            >
              {k === "all" ? `All ${countBy("all")}` : `${k} ${countBy(k)}`}
            </button>
          ))}
        </div>
        <div className="flex border border-stone-300">
          {(["all", "prime", "br", "og", "powder"] as TypeKey[]).map((k) => (
            <button
              key={k}
              onClick={() => setGtype(k)}
              className={`px-3 py-2 text-[11px] font-bold tracking-widest uppercase transition-colors ${
                gtype === k ? "bg-emerald-800 text-white" : "bg-white text-stone-600 hover:bg-stone-100"
              }`}
            >
              {k === "all" ? "All types" : k === "br" ? "BR" : k === "og" ? "OG" : "Powder"}
            </button>
          ))}
        </div>
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search grade or alternative…"
          className="min-w-[220px] flex-1 border border-stone-300 bg-white px-3 py-2 font-mono text-xs text-stone-800 placeholder:text-stone-400 focus:border-stone-500 focus:outline-none"
        />
        <div className="ml-auto font-mono text-[11px] text-stone-500">
          {rows.length} / {table.rows.length} grades
        </div>
      </div>

      {/* ============ consolidated table ============ */}
      <div className="overflow-x-auto border border-stone-200">
        <table className="w-full border-collapse text-left text-[12px]">
          <thead className="sticky top-0 z-10">
            <tr className="bg-stone-900 text-white">
              {COLUMNS.map((c) => (
                <th
                  key={c.key}
                  onClick={() => toggleSort(c.key)}
                  className={`cursor-pointer border-b border-stone-700 px-3 py-2.5 text-[10px] font-bold tracking-[0.12em] whitespace-nowrap uppercase select-none hover:bg-stone-800 ${
                    c.numeric ? "text-right" : "text-left"
                  } ${c.key === "grade" ? "sticky left-0 z-20 bg-stone-900" : ""}`}
                  title={`Sort by ${c.label}`}
                >
                  {c.label}
                  <span className="ml-1 inline-block w-2 text-emerald-400">
                    {sortKey === c.key ? (dir === 1 ? "▲" : "▼") : ""}
                  </span>
                  {c.group === "ware" && (
                    <span className="ml-1.5 font-mono text-[9px] font-normal text-stone-400" title="Ex-plant / ex-works basic price basis">
                      ex-plant
                    </span>
                  )}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => {
              const badge = TYPE_BADGE[r.grade_type];
              return (
                <tr
                  key={`${r.polymer}-${r.grade}`}
                  className={`${i % 2 ? "bg-stone-50/70" : "bg-white"} border-b border-stone-100 hover:bg-emerald-50/50`}
                >
                  {/* grade */}
                  <td className="sticky left-0 z-10 bg-inherit px-3 py-2">
                    <span className="flex items-center gap-2 whitespace-nowrap">
                      {r.tds_id ? (
                        <button
                          onClick={() => onOpenGrade(r.tds_id!)}
                          className="font-mono text-[12.5px] font-bold text-stone-900 underline decoration-emerald-600 decoration-2 underline-offset-2 hover:text-emerald-800"
                          title={`Open ${r.tds_grade} TDS sheet`}
                        >
                          {r.grade}
                        </button>
                      ) : (
                        <span className="font-mono text-[12.5px] font-bold text-stone-700">{r.grade}</span>
                      )}
                      {badge && (
                        <span
                          className={`rounded-sm border px-1 py-px text-[9px] font-bold tracking-wider ${badge.cls}`}
                          title={
                            r.grade_type === "br"
                              ? "Blending Resin"
                              : r.grade_type === "og"
                                ? "Off-Grade"
                                : "Powder grade"
                          }
                        >
                          {badge.label}
                        </span>
                      )}
                    </span>
                  </td>
                  {/* polymer */}
                  <td className="px-3 py-2 whitespace-nowrap">
                    <span className="flex items-center gap-2">
                      <span
                        className="inline-block h-2 w-2 shrink-0 rounded-full"
                        style={{ background: POLYMER_COLORS[r.polymer] ?? "#555" }}
                      />
                      <span className="text-[11.5px] font-semibold text-stone-700">{r.polymer}</span>
                    </span>
                  </td>
                  {/* manufacturer */}
                  <td className="px-3 py-2 whitespace-nowrap text-[11.5px] text-stone-600">
                    <span className="rounded-sm border border-[#C8102E]/25 bg-[#fdf2f3] px-1.5 py-0.5 font-semibold text-[#9c0c24]">
                      {r.manufacturer}
                    </span>
                  </td>
                  {/* prices */}
                  <td className="border-l border-stone-200 px-3 py-2 text-right font-mono text-[11.5px] font-semibold text-stone-800">
                    {inr(r.ex_stock_jh)}
                  </td>
                  <td className="px-3 py-2 text-right font-mono text-[11.5px] font-semibold text-stone-800">
                    {inr(r.ex_stock_br)}
                  </td>
                  <td className="border-l border-stone-200 px-3 py-2 text-right font-mono text-[11.5px] text-stone-800">
                    {inr(r.ex_ware_jh)}
                  </td>
                  <td className="px-3 py-2 text-right font-mono text-[11.5px] text-stone-800">
                    {inr(r.ex_ware_br)}
                  </td>
                  {/* haldia alternative */}
                  <td className="min-w-[190px] px-3 py-1.5">
                    {r.alts.length === 0 ? (
                      <span className="text-stone-300">—</span>
                    ) : (
                      <span className="flex flex-wrap gap-1">
                        {r.alts.map((a) => (
                          <span
                            key={a.grade}
                            className={`inline-flex items-center gap-1 border px-1.5 py-0.5 font-mono text-[10.5px] font-semibold ${
                              a.id
                                ? "cursor-pointer border-emerald-300 bg-emerald-50 text-emerald-900 hover:border-emerald-600"
                                : "border-stone-200 bg-stone-50 text-stone-600"
                            }`}
                            title={
                              a.id
                                ? `Open ${a.grade} TDS sheet`
                                : `${a.grade} — identical price column in the HPL price list`
                            }
                            onClick={a.id ? () => onOpenGrade(a.id!) : undefined}
                          >
                            <span
                              className={`inline-block h-1.5 w-1.5 rounded-full ${
                                a.src === "price"
                                  ? "bg-amber-500"
                                  : a.src === "both"
                                    ? "bg-emerald-600"
                                    : "bg-emerald-600"
                              }`}
                            />
                            {a.grade}
                          </span>
                        ))}
                      </span>
                    )}
                  </td>
                </tr>
              );
            })}
            {rows.length === 0 && (
              <tr>
                <td colSpan={8} className="px-6 py-14 text-center text-sm text-stone-500">
                  No grades match the current filters.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* ============ legend + basis notes ============ */}
      <div className="mt-4 grid gap-3 lg:grid-cols-2">
        <div className="border border-stone-200 bg-white px-4 py-3">
          <div className="mb-1.5 text-[9px] font-bold tracking-[0.2em] text-stone-400 uppercase">
            Price basis
          </div>
          <p className="text-[11.5px] leading-relaxed text-stone-600">
            <b className="text-stone-800">Ex-Stock Price</b> — {meta.ex_stock_basis}
          </p>
          <p className="mt-1.5 text-[11.5px] leading-relaxed text-stone-600">
            <b className="text-stone-800">Ex-Warehouse Price</b> — {meta.ex_warehouse_basis}
          </p>
        </div>
        <div className="border border-stone-200 bg-white px-4 py-3">
          <div className="mb-1.5 text-[9px] font-bold tracking-[0.2em] text-stone-400 uppercase">
            Reading the table
          </div>
          <ul className="space-y-1 text-[11.5px] leading-relaxed text-stone-600">
            <li>
              <span className="mr-1.5 inline-block h-1.5 w-1.5 rounded-full bg-emerald-600" />
              Alternative grade co-listed in the Polymer Competition mapping (application equivalent).
            </li>
            <li>
              <span className="mr-1.5 inline-block h-1.5 w-1.5 rounded-full bg-amber-500" />
              Shares the identical price column in the HPL price list (e.g. HDT10 &amp; HDT10S).
            </li>
            <li>
              <span className="font-mono">—</span> not published in the circular (PP powder grades are
              ex-works only). Z / non-prime grades are Rs 800/MT below the corresponding prime grade; cash
              discount Rs 1,100/MT on pre-GST basis.
            </li>
            <li>Grade names with an underline open the full technical data sheet.</li>
          </ul>
        </div>
      </div>
      <p className="mt-3 text-[10.5px] leading-relaxed text-stone-400">
        Sources: {meta.sources.join(" · ")}. Prices are basic credit prices in Rs./MT and may change
        without prior notice — the price prevailing at the time of dispatch applies.
      </p>
    </div>
  );
}
