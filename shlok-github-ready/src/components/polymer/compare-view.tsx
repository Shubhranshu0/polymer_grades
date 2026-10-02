"use client";

import { Grade } from "@/lib/polymer-types";
import { COMPANY_STYLES, POLYMER_COLORS } from "@/lib/polymer-types";

const COMPARE_ROWS: { label: string; get: (g: Grade) => string }[] = [
  { label: "Company", get: (g) => g.company_name },
  { label: "Brand / family", get: (g) => g.family || "—" },
  { label: "Polymer", get: (g) => g.polymer_label },
  { label: "Segment", get: (g) => g.segment },
  { label: "BIS designation", get: (g) => g.bis_code || "—" },
  {
    label: "MFI",
    get: (g) => (g.key.mfi ? `${g.key.mfi.value} ${g.key.mfi.unit} (${g.key.mfi.condition || "std"})` : "—"),
  },
  { label: "Density", get: (g) => (g.key.density ? `${g.key.density.value} ${g.key.density.unit}` : "—") },
  {
    label: "Tensile @ yield",
    get: (g) => (g.key.tensile_yield ? `${g.key.tensile_yield.value} ${g.key.tensile_yield.unit}` : "—"),
  },
  {
    label: "Flexural modulus",
    get: (g) => (g.key.flexural ? `${g.key.flexural.value} ${g.key.flexural.unit}` : "—"),
  },
  { label: "Izod impact", get: (g) => (g.key.izod ? `${g.key.izod.value} ${g.key.izod.unit}` : "—") },
  {
    label: "Processing temp.",
    get: (g) =>
      g.processing.length ? g.processing.map((p) => `${p.condition}: ${p.window}`).join(" · ") : "—",
  },
  {
    label: "Ex-works price (Sep 2026)",
    get: (g) =>
      g.price ? `₹ ${g.price.ex_works_ref.toLocaleString("en-IN")}/MT (ref)` : "not in circular",
  },
  { label: "Typical uses", get: (g) => g.uses.slice(0, 3).join(" · ") || "—" },
];

export function CompareView({
  selected,
  onRemove,
  onClear,
  onOpen,
}: {
  selected: Grade[];
  onRemove: (g: Grade) => void;
  onClear: () => void;
  onOpen: (g: Grade) => void;
}) {
  if (selected.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center border border-dashed border-stone-300 bg-stone-50/50 px-6 py-24 text-center">
        <div className="mb-3 text-4xl">⚖️</div>
        <h3 className="font-mono text-lg font-bold text-stone-800">Comparison tray is empty</h3>
        <p className="mt-2 max-w-md text-sm leading-relaxed text-stone-500">
          Add grades from the Grade Book using the <span className="font-mono font-bold">+</span> button on any card, then
          compare up to four sheets side-by-side — MFI, density, mechanicals, processing windows and September price
          points.
        </p>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          {selected.map((g) => {
            const comp = COMPANY_STYLES[g.company] ?? { color: "#555", bg: "#f5f5f5", label: "?" };
            return (
              <span
                key={g.id}
                className="inline-flex items-center gap-2 border px-3 py-1.5 font-mono text-xs font-bold"
                style={{ borderColor: comp.color, color: comp.color, background: comp.bg }}
              >
                {g.grade}
                <button onClick={() => onRemove(g)} aria-label={`Remove ${g.grade}`} className="opacity-60 hover:opacity-100">
                  ×
                </button>
              </span>
            );
          })}
        </div>
        <button
          onClick={onClear}
          className="rounded-sm border border-stone-300 px-3 py-1.5 text-[11px] font-bold tracking-widest text-stone-600 uppercase hover:border-stone-600 hover:text-stone-900"
        >
          Clear all
        </button>
      </div>

      <div className="overflow-x-auto border border-stone-200">
        <table className="w-full min-w-[760px] border-collapse text-left text-[13px]">
          <thead>
            <tr className="border-b border-stone-200 bg-stone-100">
              <th className="w-44 px-4 py-3 text-[10px] font-bold tracking-[0.16em] text-stone-500 uppercase">
                Parameter
              </th>
              {selected.map((g) => {
                const comp = COMPANY_STYLES[g.company] ?? { color: "#555", bg: "#f5f5f5", label: "?" };
                return (
                  <th key={g.id} className="px-4 py-3 align-top">
                    <button
                      onClick={() => onOpen(g)}
                      className="text-left font-mono text-base font-bold underline decoration-dotted underline-offset-4 hover:opacity-75"
                      style={{ color: comp.color }}
                    >
                      {g.grade}
                    </button>
                    <div className="mt-0.5 text-[10px] font-semibold tracking-wide uppercase" style={{ color: POLYMER_COLORS[g.polymer] ?? "#555" }}>
                      {g.polymer} · {g.segment}
                    </div>
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {COMPARE_ROWS.map((row, i) => (
              <tr key={row.label} className={`border-b border-stone-100 ${i % 2 ? "bg-stone-50/60" : "bg-white"}`}>
                <td className="px-4 py-2.5 text-[11px] font-bold tracking-wide text-stone-500 uppercase">
                  {row.label}
                </td>
                {selected.map((g) => (
                  <td key={g.id} className="px-4 py-2.5 font-medium text-stone-800">
                    {row.get(g)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* full property union table */}
      <h3 className="mt-8 mb-3 flex items-center gap-2 text-[11px] font-bold tracking-[0.22em] text-stone-500 uppercase">
        <span className="inline-block h-2 w-2 bg-stone-500" />
        Full TDS property union
      </h3>
      <PropertyUnion grades={selected} />
    </div>
  );
}

function PropertyUnion({ grades }: { grades: Grade[] }) {
  // union of property names, in first-seen order
  const names: string[] = [];
  for (const g of grades) {
    for (const p of g.props) {
      if (!names.includes(p.name)) names.push(p.name);
    }
  }
  const lookup = (g: Grade, name: string) => g.props.find((p) => p.name === name);

  return (
    <div className="overflow-x-auto border border-stone-200">
      <table className="w-full min-w-[760px] border-collapse text-left text-[13px]">
        <thead>
          <tr className="bg-stone-100 text-[10px] font-bold tracking-[0.14em] text-stone-500 uppercase">
            <th className="w-64 px-4 py-2.5">Property</th>
            {grades.map((g) => (
              <th key={g.id} className="px-4 py-2.5 font-mono text-xs text-stone-700">
                {g.grade}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {names.map((name, i) => (
            <tr key={name} className={`border-b border-stone-100 ${i % 2 ? "bg-stone-50/60" : "bg-white"}`}>
              <td className="px-4 py-2 font-medium text-stone-800">{name}</td>
              {grades.map((g) => {
                const p = lookup(g, name);
                return (
                  <td key={g.id} className="px-4 py-2 font-mono text-stone-700">
                    {p ? `${p.value}${p.unit ? ` ${p.unit}` : ""}` : <span className="text-stone-300">—</span>}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
