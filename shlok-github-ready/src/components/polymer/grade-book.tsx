"use client";

import { useMemo, useState } from "react";
import { Grade } from "@/lib/polymer-types";
import { GradeCard } from "./grade-card";

const POLY_FILTERS = [
  ["all", "All polymers"],
  ["HDPE", "HDPE"],
  ["LLDPE", "LLDPE"],
  ["LDPE", "LDPE"],
  ["PP", "PP (all types)"],
  ["PP-Homo", "PP Homo"],
  ["PP-Random", "PP Random"],
  ["PP-Impact", "PP Impact"],
] as const;

function polymerMatches(filter: string, polymer: string) {
  if (filter === "all") return true;
  if (filter === "PP") return polymer === "PP" || polymer.startsWith("PP-");
  return polymer === filter;
}

export function GradeBook({
  grades,
  onOpen,
  onCompare,
  selectedIds,
}: {
  grades: Grade[];
  onOpen: (g: Grade) => void;
  onCompare: (g: Grade) => void;
  selectedIds: Set<string>;
}) {
  const [poly, setPoly] = useState<string>("all");
  const [query, setQuery] = useState("");

  const segments = useMemo(() => {
    const s = new Set<string>();
    for (const g of grades) s.add(g.segment);
    return Array.from(s).sort();
  }, [grades]);
  const [segment, setSegment] = useState<string>("all");

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return grades.filter((g) => {
      if (!polymerMatches(poly, g.polymer)) return false;
      if (segment !== "all" && g.segment !== segment) return false;
      if (q) {
        // searching a competitor grade code surfaces the Haldia grades that
        // compete with it (mapping lives in the Competition tab)
        const competedCodes = (g.competed_by ?? []).map((c) => c.grade).join(" ");
        const hay = `${g.grade} ${g.alt_codes?.join(" ") ?? ""} ${g.family} ${g.polymer} ${g.segment} ${g.uses.join(" ")} ${g.bis_code} ${g.desc.join(" ")} ${competedCodes}`.toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });
  }, [grades, poly, segment, query]);

  return (
    <div>
      {/* filter bar */}
      <div className="sticky top-[57px] z-30 -mx-4 mb-6 border-b border-stone-200 bg-stone-50/95 px-4 py-3 backdrop-blur sm:top-[61px] sm:mx-0 sm:rounded-sm sm:border sm:px-4">
        <div className="flex flex-wrap items-center gap-2.5">
          {/* search */}
          <div className="relative min-w-[220px] flex-1">
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search grade, use, BIS code…"
              className="w-full rounded-sm border border-stone-300 bg-white px-3.5 py-2 pl-8 text-sm text-stone-800 placeholder:text-stone-400 focus:border-stone-900 focus:outline-none"
              aria-label="Search grades"
            />
            <svg
              className="absolute top-1/2 left-2.5 h-3.5 w-3.5 -translate-y-1/2 text-stone-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2.5}
            >
              <circle cx="11" cy="11" r="7" />
              <path d="m21 21-4.3-4.3" />
            </svg>
          </div>

          {/* polymer select */}
          <select
            value={poly}
            onChange={(e) => setPoly(e.target.value)}
            className="rounded-sm border border-stone-300 bg-white px-2.5 py-1.5 text-xs font-semibold text-stone-700 focus:border-stone-900 focus:outline-none"
            aria-label="Filter by polymer"
          >
            {POLY_FILTERS.map(([k, label]) => (
              <option key={k} value={k}>
                {label}
              </option>
            ))}
          </select>

          {/* segment select */}
          <select
            value={segment}
            onChange={(e) => setSegment(e.target.value)}
            className="max-w-[190px] rounded-sm border border-stone-300 bg-white px-2.5 py-1.5 text-xs font-semibold text-stone-700 focus:border-stone-900 focus:outline-none"
            aria-label="Filter by application segment"
          >
            <option value="all">All segments</option>
            {segments.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>

          <div className="ml-auto font-mono text-xs text-stone-500">
            <span className="font-bold text-stone-800">{filtered.length}</span> / {grades.length} sheets
          </div>
        </div>
      </div>

      {/* results grid */}
      {filtered.length === 0 ? (
        <div className="border border-dashed border-stone-300 px-6 py-20 text-center">
          <p className="font-mono text-sm font-bold text-stone-700">No Halene grades match the current filters.</p>
          <p className="mt-1 text-xs text-stone-500">
            Try clearing the search or widening the filters. Searching a competitor grade code will surface the Halene
            grades that compete with it.
          </p>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {filtered.map((g) => (
            <GradeCard
              key={g.id}
              grade={g}
              onOpen={onOpen}
              onCompare={onCompare}
              selected={selectedIds.has(g.id)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
