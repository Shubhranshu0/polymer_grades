"use client";

import { Grade } from "@/lib/polymer-types";
import { COMPANY_STYLES, POLYMER_COLORS } from "@/lib/polymer-types";
import { getHaldiaGradeById } from "./grade-sheet";

function fmtMfi(g: Grade) {
  const m = g.key.mfi;
  if (!m) return { value: "—", cond: "" };
  return { value: `${m.value} ${m.unit}`, cond: m.condition || "" };
}

function fmtDensity(g: Grade) {
  const d = g.key.density;
  if (!d) return { value: "—", cond: "" };
  return { value: `${d.value} ${d.unit}`, cond: "23°C" };
}

export function GradeCard({
  grade,
  onOpen,
  onCompare,
  selected,
}: {
  grade: Grade;
  onOpen: (g: Grade) => void;
  onCompare: (g: Grade) => void;
  selected: boolean;
}) {
  const comp = COMPANY_STYLES[grade.company] ?? { color: "#555", bg: "#f5f5f5", label: "?" };
  const polyColor = POLYMER_COLORS[grade.polymer] ?? "#555";
  const mfi = fmtMfi(grade);
  const dens = fmtDensity(grade);
  const desc = grade.desc.join(" ").slice(0, 200);

  return (
    <article
      className="group relative flex h-full flex-col border border-stone-200 bg-white p-5 transition-all hover:border-stone-400 hover:shadow-md"
      style={selected ? { borderColor: comp.color, boxShadow: `0 0 0 1px ${comp.color}` } : undefined}
    >
      {/* top meta row */}
      <div className="mb-3 flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div
            className="inline-flex items-center gap-1.5 text-[10px] font-bold tracking-[0.14em] uppercase"
            style={{ color: comp.color }}
          >
            <span className="inline-block h-1.5 w-1.5 rounded-full" style={{ background: comp.color }} />
            {grade.family || grade.company_name.split(" ")[0]}
            <span className="font-medium text-stone-400">· {grade.polymer}</span>
          </div>
          <h3 className="mt-1.5 truncate font-mono text-xl font-bold tracking-tight text-stone-900" title={grade.grade}>
            {grade.grade}
          </h3>
          <div className="mt-0.5 truncate text-xs font-semibold tracking-wide uppercase" style={{ color: polyColor }}>
            {grade.segment}
          </div>
        </div>
        <button
          onClick={() => onCompare(grade)}
          aria-label={selected ? "Remove from comparison" : "Add to comparison"}
          className={`mt-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-full border text-xs font-bold transition-colors ${
            selected
              ? "border-transparent text-white"
              : "border-stone-300 text-stone-500 hover:border-stone-500 hover:text-stone-800"
          }`}
          style={selected ? { background: comp.color } : undefined}
          title={selected ? "In comparison" : "Compare"}
        >
          {selected ? "✓" : "+"}
        </button>
      </div>

      {/* description */}
      <p className="mb-4 line-clamp-3 text-[13px] leading-relaxed text-stone-600">{desc || "—"}</p>

      {/* MFI / Density stats */}
      <div className="mb-4 grid grid-cols-2 divide-x divide-stone-200 border-y border-stone-200 py-3">
        <div className="pr-3">
          <div className="text-[9px] font-bold tracking-[0.18em] text-stone-400 uppercase">Melt Flow Index</div>
          <div className="mt-0.5 font-mono text-sm font-bold text-stone-900">{mfi.value}</div>
          <div className="truncate text-[10px] text-stone-500">{mfi.cond}</div>
        </div>
        <div className="pl-3">
          <div className="text-[9px] font-bold tracking-[0.18em] text-stone-400 uppercase">Density</div>
          <div className="mt-0.5 font-mono text-sm font-bold text-stone-900">{dens.value}</div>
          <div className="truncate text-[10px] text-stone-500">
            {grade.bis_code ? `BIS · ${grade.bis_code}` : grade.uses[0]?.slice(0, 26) ?? ""}
          </div>
        </div>
      </div>

      {/* uses + price + alternates */}
      <div className="mb-4 flex-1 space-y-2">
        {grade.uses.length > 0 && (
          <div className="text-xs leading-relaxed text-stone-600">
            <span className="font-bold tracking-wide text-stone-800 uppercase">Uses · </span>
            {grade.uses.slice(0, 3).join(" · ")}
          </div>
        )}
        {grade.price ? (
          <div className="flex flex-wrap items-baseline gap-x-2 text-xs">
            <span className="rounded-sm bg-emerald-50 px-1.5 py-0.5 font-mono font-bold text-emerald-800">
              ₹ {(grade.price.ex_works_ref / 1000).toFixed(1)}k/MT
            </span>
            <span className="text-[10px] text-stone-500">
              ex-works range ₹{(grade.price.ex_works_min / 1000).toFixed(1)}k–
              {(grade.price.ex_works_max / 1000).toFixed(1)}k · eff. {grade.price.effective}
            </span>
          </div>
        ) : null}

        {/* alternate Haldia grades (competitor cards — Grade Book lists Haldia only;
            kept for reuse when cards are opened from the Competition tab) */}
        {grade.company !== "haldia" && grade.competition && (
          <div className="flex flex-wrap items-center gap-1.5 text-[11px]">
            <span className="font-bold tracking-wide text-[#C8102E] uppercase">Haldia alternate</span>
            {(grade.competition.alt_haldia_ids ?? []).length > 0 ? (
              (grade.competition.alt_haldia_ids ?? []).map((a) => (
                <button
                  key={a.id}
                  onClick={() => {
                    const hg = getHaldiaGradeById(a.id);
                    if (hg) onOpen(hg);
                  }}
                  title={`Open Haldia ${a.grade} data sheet`}
                  className="rounded-sm border border-[#C8102E]/40 bg-[#fdf2f3] px-1.5 py-0.5 font-mono text-[11px] font-bold text-[#C8102E] transition-colors hover:border-[#C8102E] hover:bg-[#C8102E] hover:text-white"
                >
                  {grade.competition?.alt_match_kind === "closest" ? `~${a.grade}` : a.grade}
                </button>
              ))
            ) : (
              <span className="text-stone-400">no direct equivalent</span>
            )}
          </div>
        )}
      </div>

      {/* actions */}
      <div className="flex items-center gap-2 border-t border-stone-100 pt-3">
        <button
          onClick={() => onOpen(grade)}
          className="flex-1 rounded-sm bg-stone-900 px-3 py-2 text-xs font-bold tracking-widest text-white uppercase transition-colors hover:bg-stone-700"
        >
          Open sheet
        </button>
        <button
          onClick={() => onCompare(grade)}
          className="rounded-sm border border-stone-300 px-3 py-2 text-xs font-bold tracking-widest text-stone-700 uppercase transition-colors hover:border-stone-600 hover:text-stone-950"
        >
          Compare
        </button>
      </div>
    </article>
  );
}
