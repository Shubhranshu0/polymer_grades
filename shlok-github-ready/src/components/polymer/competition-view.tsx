"use client";

import { useMemo, useState } from "react";
import { Grade, CompetedByRef } from "@/lib/polymer-types";
import { COMPANY_STYLES } from "@/lib/polymer-types";
import { getGradeById } from "./grade-sheet";

type Mode = "competitors" | "haldia";

function polymerMatches(filter: string, polymer: string) {
  if (filter === "all") return true;
  if (filter === "PP") return polymer === "PP" || polymer.startsWith("PP-");
  return polymer === filter;
}

const POLY_OPTIONS = [
  ["all", "All polymers"],
  ["HDPE", "HDPE"],
  ["LLDPE", "LLDPE"],
  ["LDPE", "LDPE"],
  ["PP", "PP (all)"],
  ["PP-Homo", "PP-Homo"],
  ["PP-Random", "PP-Random"],
  ["PP-Impact", "PP-Impact"],
] as const;

export function CompetitionView({
  grades,
  onOpen,
  onOpenGrade,
}: {
  grades: Grade[];
  onOpen: (g: Grade) => void;
  onOpenGrade: (g: Grade) => void;
}) {
  const [company, setCompany] = useState<string>("all");
  const [poly, setPoly] = useState<string>("all");
  const [mode, setMode] = useState<Mode>("competitors");

  const competitorRows = useMemo(
    () =>
      grades.filter(
        (g) =>
          g.company !== "haldia" &&
          g.competition &&
          (company === "all" || g.company === company) &&
          polymerMatches(poly, g.polymer)
      ),
    [grades, company, poly]
  );

  const haldiaRows = useMemo(
    () =>
      grades.filter(
        (g) =>
          g.company === "haldia" &&
          (g.competed_by?.length ?? 0) > 0 &&
          polymerMatches(poly, g.polymer) &&
          (company === "all" || (g.competed_by ?? []).some((c) => c.company === company))
      ),
    [grades, company, poly]
  );

  const openComp = (id: string) => {
    const g = getGradeById(id);
    if (g) onOpenGrade(g);
  };

  return (
    <div>
      <p className="mb-4 max-w-3xl text-sm leading-relaxed text-stone-600">
        Grade-by-grade competitive mapping of Reliance (Relene / Repol), IOCL (Propel) and OPaL polymer portfolios against
        the Haldia Halene range — with the published rationale for where the Haldia grade is stronger. Every competitor
        grade shows its <b>alternate Haldia grade(s)</b>; every Haldia grade lists the competitor grades mapped against
        it. Click any highlighted code to open its full TDS sheet. A <span className="font-mono">~</span> prefix marks a
        nearest-substitute mapping where no true Haldia equivalent exists.
      </p>

      {/* filters */}
      <div className="mb-4 flex flex-wrap items-center gap-3">
        {/* mode toggle */}
        <div className="flex border border-stone-300">
          {(
            [
              ["competitors", "By competitor grade"],
              ["haldia", "By Haldia grade"],
            ] as [Mode, string][]
          ).map(([k, label]) => (
            <button
              key={k}
              onClick={() => setMode(k)}
              className={`px-3.5 py-1.5 text-xs font-bold tracking-widest uppercase transition-colors ${
                mode === k ? "bg-stone-900 text-white" : "bg-white text-stone-600 hover:bg-stone-100"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
        {mode === "competitors" && (
          <div className="flex border border-stone-300">
            {[
              ["all", "All"],
              ["reliance", "Reliance"],
              ["iocl", "IOCL"],
              ["ongc", "OPaL"],
            ].map(([k, label]) => (
              <button
                key={k}
                onClick={() => setCompany(k)}
                className={`px-3.5 py-1.5 text-xs font-bold tracking-widest uppercase transition-colors ${
                  company === k ? "bg-stone-900 text-white" : "bg-white text-stone-600 hover:bg-stone-100"
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        )}
        <div className="flex flex-wrap border border-stone-300">
          {POLY_OPTIONS.map(([k, label]) => (
            <button
              key={k}
              onClick={() => setPoly(k)}
              className={`px-3 py-1.5 text-xs font-bold tracking-widest uppercase transition-colors ${
                poly === k ? "bg-stone-900 text-white" : "bg-white text-stone-600 hover:bg-stone-100"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
        <div className="ml-auto self-center font-mono text-xs text-stone-500">
          {mode === "competitors"
            ? `${competitorRows.length} competitor grades`
            : `${haldiaRows.length} Haldia grades · ${haldiaRows.reduce((a, g) => a + (g.competed_by?.length ?? 0), 0)} mappings`}
        </div>
      </div>

      {mode === "competitors" ? (
        <div className="overflow-x-auto border border-stone-200">
          <table className="w-full min-w-[980px] border-collapse text-left text-[12.5px]">
            <thead>
              <tr className="bg-stone-900 text-[10px] font-bold tracking-[0.14em] text-stone-200 uppercase">
                <th className="px-3 py-2.5">Competitor grade</th>
                <th className="px-3 py-2.5">Polymer · segment</th>
                <th className="px-3 py-2.5">MFI / density</th>
                <th className="px-3 py-2.5">Alternate Haldia grade(s)</th>
                <th className="px-3 py-2.5">Why Haldia is stronger</th>
                <th className="px-3 py-2.5"></th>
              </tr>
            </thead>
            <tbody>
              {competitorRows.map((g, i) => {
                const comp = COMPANY_STYLES[g.company];
                const c = g.competition!;
                const alts = c.alt_haldia_ids ?? [];
                return (
                  <tr key={g.id} className={`border-b border-stone-100 align-top ${i % 2 ? "bg-stone-50/60" : "bg-white"}`}>
                    <td className="px-3 py-2.5">
                      <div className="font-mono text-sm font-bold" style={{ color: comp.color }}>
                        {g.grade}
                      </div>
                      <div className="text-[10px] font-semibold tracking-wide text-stone-400 uppercase">{comp.label}</div>
                    </td>
                    <td className="px-3 py-2.5">
                      <div className="font-medium text-stone-800">{g.polymer}</div>
                      <div className="text-[11px] text-stone-500">{g.segment}</div>
                    </td>
                    <td className="px-3 py-2.5 font-mono text-[11px] text-stone-600">
                      {g.key.mfi ? `${g.key.mfi.value} ${g.key.mfi.unit}` : "—"}
                      <br />
                      {g.key.density ? g.key.density.value : "—"}
                    </td>
                    <td className="px-3 py-2.5">
                      {alts.length > 0 ? (
                        <div className="flex flex-wrap gap-1">
                          {alts.map((a) => (
                            <button
                              key={a.id}
                              onClick={() => openComp(a.id)}
                              title={`Open Haldia ${a.grade} data sheet`}
                              className="border border-[#C8102E]/40 bg-[#fdf2f3] px-1.5 py-0.5 font-mono text-xs font-bold text-[#C8102E] transition-colors hover:border-[#C8102E] hover:bg-[#C8102E] hover:text-white"
                            >
                              {c.alt_match_kind === "closest" ? `~${a.grade}` : a.grade}
                            </button>
                          ))}
                        </div>
                      ) : (
                        <span className="font-mono text-[11px] text-stone-400">{c.haldia_alt || "N/A"}</span>
                      )}
                      {c.auto_mapped && (
                        <div className="mt-1 text-[10px] font-semibold text-amber-700 uppercase">auto-mapped</div>
                      )}
                      {c.haldia_grade_superior && (
                        <div className="mt-1 max-w-[220px] text-[10.5px] leading-snug text-stone-500">{c.haldia_grade_superior}</div>
                      )}
                    </td>
                    <td className="max-w-[340px] px-3 py-2.5 text-[11.5px] leading-relaxed text-stone-600">
                      {(c.reason_haldia_better || c.comparison || "—").slice(0, 260)}
                      {(c.reason_haldia_better || c.comparison || "").length > 260 ? "…" : ""}
                    </td>
                    <td className="px-3 py-2.5">
                      <button
                        onClick={() => onOpen(g)}
                        className="rounded-sm border border-stone-300 px-2.5 py-1 text-[10px] font-bold tracking-widest text-stone-600 uppercase hover:border-stone-600 hover:text-stone-900"
                      >
                        Sheet
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="overflow-x-auto border border-stone-200">
          <table className="w-full min-w-[860px] border-collapse text-left text-[12.5px]">
            <thead>
              <tr className="bg-[#C8102E] text-[10px] font-bold tracking-[0.14em] text-white uppercase">
                <th className="px-3 py-2.5">Haldia grade</th>
                <th className="px-3 py-2.5">Polymer · segment</th>
                <th className="px-3 py-2.5">MFI / density</th>
                <th className="px-3 py-2.5">Competitor grades mapped to it</th>
                <th className="px-3 py-2.5"></th>
              </tr>
            </thead>
            <tbody>
              {haldiaRows.map((g, i) => {
                const byCompany: Record<string, CompetedByRef[]> = {};
                for (const c of g.competed_by ?? []) {
                  (byCompany[c.company] ??= []).push(c);
                }
                return (
                  <tr key={g.id} className={`border-b border-stone-100 align-top ${i % 2 ? "bg-stone-50/60" : "bg-white"}`}>
                    <td className="px-3 py-2.5">
                      <div className="font-mono text-sm font-bold text-[#C8102E]">{g.grade}</div>
                      <div className="text-[10px] font-semibold tracking-wide text-stone-400 uppercase">Halene · HPL</div>
                    </td>
                    <td className="px-3 py-2.5">
                      <div className="font-medium text-stone-800">{g.polymer}</div>
                      <div className="text-[11px] text-stone-500">{g.segment}</div>
                    </td>
                    <td className="px-3 py-2.5 font-mono text-[11px] text-stone-600">
                      {g.key.mfi ? `${g.key.mfi.value} ${g.key.mfi.unit}` : "—"}
                      <br />
                      {g.key.density ? g.key.density.value : "—"}
                    </td>
                    <td className="px-3 py-2.5">
                      <div className="flex flex-wrap gap-1">
                        {Object.entries(byCompany).map(([co, refs]) => {
                          const cs = COMPANY_STYLES[co] ?? { color: "#555", bg: "#f5f5f5", label: co };
                          return refs.map((c, idx) => (
                            <button
                              key={`${c.id}-${idx}`}
                              onClick={() => openComp(c.id)}
                              title={`${cs.label} · ${c.polymer}${c.kind === "closest" ? " · nearest-substitute mapping" : c.kind === "secondary" ? " · referenced in comparison notes" : ""}`}
                              className="border px-1.5 py-0.5 font-mono text-xs font-bold transition-colors hover:text-white"
                              style={{ borderColor: cs.color, color: cs.color, background: cs.bg }}
                              onMouseEnter={(e) => (e.currentTarget.style.background = cs.color)}
                              onMouseLeave={(e) => (e.currentTarget.style.background = cs.bg)}
                            >
                              {c.kind === "closest" ? `~${c.grade}` : c.grade}
                              <span className="ml-1 text-[9px] opacity-70">{cs.label}</span>
                            </button>
                          ));
                        })}
                      </div>
                    </td>
                    <td className="px-3 py-2.5">
                      <button
                        onClick={() => onOpen(g)}
                        className="rounded-sm border border-stone-300 px-2.5 py-1 text-[10px] font-bold tracking-widest text-stone-600 uppercase hover:border-stone-600 hover:text-stone-900"
                      >
                        Sheet
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
