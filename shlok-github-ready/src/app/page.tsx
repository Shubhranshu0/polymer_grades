"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Image from "next/image";
import { Dataset, Grade, POLYMER_COLORS } from "@/lib/polymer-types";
import { setAllGradesCache, setHaldiaGradesCache } from "@/components/polymer/grade-sheet";
import { GradeBook } from "@/components/polymer/grade-book";
import { GradeSheet } from "@/components/polymer/grade-sheet";
import { CompareView } from "@/components/polymer/compare-view";
import { PricesView } from "@/components/polymer/prices-view";
import { CompetitionView } from "@/components/polymer/competition-view";
import { ContactView } from "@/components/polymer/contact-view";
import { OrderView } from "@/components/polymer/order-view";

type View = "book" | "compare" | "prices" | "order" | "competition" | "contact";

export default function Home() {
  const [data, setData] = useState<Dataset | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [view, setView] = useState<View>("book");
  const [sheetGrade, setSheetGrade] = useState<Grade | null>(null);
  const [selected, setSelected] = useState<Grade[]>([]);

  useEffect(() => {
    fetch("/data/dataset.json")
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((d: Dataset) => {
        setData(d);
        setHaldiaGradesCache(d.grades.filter((g) => g.company === "haldia"));
        setAllGradesCache(d.grades);
      })
      .catch((e) => setError(String(e)));
  }, []);

  const toggleCompare = useCallback((g: Grade) => {
    setSelected((sel) => {
      if (sel.find((s) => s.id === g.id)) return sel.filter((s) => s.id !== g.id);
      if (sel.length >= 4) return [...sel.slice(1), g];
      return [...sel, g];
    });
  }, []);

  const openGrade = useCallback((g: Grade) => setSheetGrade(g), []);

  const openGradeById = useCallback(
    (id: string) => {
      const g = data?.grades.find((x) => x.id === id);
      if (g) setSheetGrade(g);
    },
    [data]
  );

  const stats = useMemo(() => {
    if (!data) return null;
    const haldia = data.grades.filter((g) => g.company === "haldia");
    const families = haldia.reduce<Record<string, number>>((acc, g) => {
      acc[g.polymer] = (acc[g.polymer] || 0) + 1;
      return acc;
    }, {});
    return { haldia, families };
  }, [data]);

  if (error) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-stone-50 p-8">
        <div className="border border-red-300 bg-red-50 px-6 py-4 text-sm text-red-800">
          Failed to load dataset: {error}
        </div>
      </main>
    );
  }

  if (!data || !stats) {
    return (
      <main className="flex min-h-screen flex-col items-center justify-center gap-4 bg-stone-50">
        <div className="h-10 w-10 animate-spin rounded-full border-[3px] border-stone-200 border-t-[#EA0C2F]" />
        <p className="font-mono text-xs tracking-[0.2em] text-stone-500 uppercase">Loading grade sheets…</p>
      </main>
    );
  }

  return (
    <div className="flex min-h-screen flex-col bg-stone-50">
      {/* ============ header ============ */}
      <header className="sticky top-0 z-40 border-b border-stone-200 bg-white">
        <div className="mx-auto flex h-14 max-w-[1400px] items-center gap-4 px-4 sm:h-16 sm:px-6">
          <div className="relative h-8 w-32 shrink-0 sm:h-10 sm:w-40">
            <Image src="/shlok-logo.png" alt="SHLOK logo" fill sizes="160px" className="object-contain object-left" priority />
          </div>
          <div className="hidden h-6 w-px bg-stone-200 sm:block" />
          <div className="hidden min-w-0 sm:block">
            <div className="text-[9px] font-bold tracking-[0.28em] text-stone-400 uppercase">Polymer grade book</div>
            <div className="truncate text-sm font-bold text-stone-800">TDS · Comparison · Prices</div>
          </div>

          <nav className="ml-auto flex items-center gap-1 overflow-x-auto" aria-label="Main navigation">
            {(
              [
                ["book", "Grade Book"],
                ["compare", `Compare${selected.length ? ` (${selected.length})` : ""}`],
                ["prices", "Prices"],
                ["order", "Order"],
                ["competition", "Competition"],
                ["contact", "Contact"],
              ] as [View, string][]
            ).map(([k, label]) => (
              <button
                key={k}
                onClick={() => setView(k)}
                className={`rounded-sm px-3 py-2 text-[11px] font-bold tracking-widest whitespace-nowrap uppercase transition-colors ${
                  view === k
                    ? "bg-stone-900 text-white"
                    : k === "order"
                      ? "text-[#EA0C2F] hover:bg-red-50 hover:text-[#B00A26]"
                      : "text-stone-500 hover:bg-stone-100 hover:text-stone-900"
                }`}
              >
                {label}
              </button>
            ))}
          </nav>
        </div>
      </header>

      {/* ============ hero (only on book view) ============ */}
      {view === "book" && (
        <section className="border-b border-stone-200 bg-white">
          <div className="mx-auto max-w-[1400px] px-4 py-8 sm:px-6 sm:py-10">
            <div className="text-[10px] font-bold tracking-[0.3em] text-[#EA0C2F] uppercase">
              Haldia Petrochemicals · Halene range · {data.price_table?.meta?.period_label ?? ""}
            </div>
            <h1 className="mt-2 max-w-3xl font-serif text-3xl leading-tight font-bold tracking-tight text-stone-900 sm:text-[2.6rem]">
              Halene HDPE, LLDPE and PP grade book
            </h1>
            <p className="mt-3 max-w-3xl text-sm leading-relaxed text-stone-600">
              Typical properties, processing windows and BIS codes for the complete <b>Halene range — {stats?.haldia.length ?? 0} grades</b> from
              Haldia Petrochemicals. Every grade sheet carries its <b>alternate-grade cross-reference</b>, and the price list
              covers <b>ex-stock and ex-warehouse prices for Jharkhand &amp; Bihar</b>. Looking for what a competitor grade maps
              to? The <b>Competition</b> tab lists every Reliance, IOCL and OPaL grade against its Haldia equivalent.
            </p>

            {/* stat chips */}
            <div className="mt-6 flex flex-wrap gap-2">
              {[
                ["HDPE", "HDPE"],
                ["LLDPE", "LLDPE"],
                ["PP", "PP (all types)"],
              ].map(([k, label]) => {
                const n = stats?.families[k] ?? 0;
                const color = POLYMER_COLORS[k] ?? "#555";
                return (
                  <div
                    key={k}
                    className="flex items-center gap-2.5 border border-stone-200 bg-stone-50 px-3.5 py-2 text-left"
                  >
                    <span className="inline-block h-2 w-2 rounded-full" style={{ background: color }} />
                    <span>
                      <span className="block text-[9px] font-bold tracking-[0.16em] text-stone-500 uppercase">{label}</span>
                      <span className="font-mono text-sm font-bold text-stone-900">{n} grades</span>
                    </span>
                  </div>
                );
              })}
              <div className="flex items-center gap-2.5 border border-stone-200 bg-stone-50 px-3.5 py-2">
                <span>
                  <span className="block text-[9px] font-bold tracking-[0.16em] text-stone-500 uppercase">Halene range</span>
                  <span className="font-mono text-sm font-bold text-stone-900">
                    {stats?.haldia.length ?? 0} TDS sheets
                  </span>
                </span>
              </div>
              <button
                onClick={() => setView("prices")}
                className="flex items-center gap-2.5 border border-emerald-300 bg-emerald-50 px-3.5 py-2 text-left transition-colors hover:border-emerald-500"
              >
                <span>
                  <span className="block text-[9px] font-bold tracking-[0.16em] text-emerald-700 uppercase">Price list</span>
                  <span className="font-mono text-sm font-bold text-emerald-900">Jharkhand &amp; Bihar →</span>
                </span>
              </button>
              <button
                onClick={() => setView("order")}
                className="flex items-center gap-2.5 border border-[#EA0C2F] bg-[#EA0C2F] px-3.5 py-2 text-left transition-colors hover:border-[#C50A27] hover:bg-[#C50A27]"
              >
                <span>
                  <span className="block text-[9px] font-bold tracking-[0.16em] text-white/80 uppercase">
                    Purchase enquiry
                  </span>
                  <span className="font-mono text-sm font-bold text-white">Place your order →</span>
                </span>
              </button>
            </div>
          </div>
        </section>
      )}

      {/* ============ main content ============ */}
      <main className="mx-auto w-full max-w-[1400px] flex-1 px-4 py-8 sm:px-6">
        {view === "book" && (
          <GradeBook grades={stats.haldia} onOpen={openGrade} onCompare={toggleCompare} selectedIds={new Set(selected.map((s) => s.id))} />
        )}
        {view === "compare" && (
          <CompareView
            selected={selected}
            onRemove={toggleCompare}
            onClear={() => setSelected([])}
            onOpen={openGrade}
          />
        )}
        {view === "prices" && <PricesView table={data.price_table} onOpenGrade={openGradeById} />}
        {view === "order" && <OrderView />}
        {view === "competition" && <CompetitionView grades={data.grades} onOpen={openGrade} onOpenGrade={openGrade} />}
        {view === "contact" && <ContactView onGoOrder={() => setView("order")} />}
      </main>

      {/* ============ footer ============ */}
      <footer className="mt-auto border-t border-stone-200 bg-white">
        <div className="mx-auto max-w-[1400px] px-4 py-8 sm:px-6">
          <div className="flex flex-wrap items-start justify-between gap-6">
            <div>
              <div className="font-mono text-sm font-bold tracking-widest text-stone-800 uppercase">SHLOK</div>
              <p className="mt-2 max-w-md text-[11.5px] leading-relaxed text-stone-500">
                Polymer grade book compiled from official technical data sheets and the {data.price_table?.meta?.period_label ?? "latest"} HPL price
                circulars. Values are typical nominal data published by the producers and must not be construed as
                specifications. Compiled {data.meta.generated}.
              </p>
              <div className="mt-3 space-y-1 text-[11px] text-stone-600">
                <div>
                  <a href="mailto:shubhranshu.dca.haldia@gmail.com" className="font-mono hover:text-emerald-800 hover:underline">
                    shubhranshu.dca.haldia@gmail.com
                  </a>
                </div>
                <div className="font-mono">
                  <a href="tel:+916370284496" className="hover:text-emerald-800 hover:underline">+91 63702 84496</a>
                </div>
                <div>
                  <a
                    href="https://www.linkedin.com/in/shubhranshu-polymer-engineer"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="font-mono hover:text-emerald-800 hover:underline"
                  >
                    www.linkedin.com/in/shubhranshu-polymer-engineer
                  </a>
                </div>
                <div className="pt-1.5">
                  <button
                    onClick={() => setView("order")}
                    className="border border-[#EA0C2F] bg-[#EA0C2F] px-3.5 py-2 text-[10px] font-bold tracking-widest text-white uppercase transition-colors hover:border-[#C50A27] hover:bg-[#C50A27]"
                  >
                    Place a purchase order →
                  </button>
                </div>
              </div>
            </div>
            <div className="text-[11px] leading-relaxed text-stone-500">
              <div className="mb-1.5 text-[9px] font-bold tracking-[0.2em] text-stone-400 uppercase">Sources</div>
              {data.meta.source_pdfs.map((s) => (
                <div key={s} className="font-mono text-[10.5px]">
                  · {s}
                </div>
              ))}
            </div>
            <div className="text-[11px] leading-relaxed text-stone-500">
              <div className="mb-1.5 text-[9px] font-bold tracking-[0.2em] text-stone-400 uppercase">Halene grade counts</div>
              <div className="font-mono text-[10.5px]">· Haldia (Halene): {stats.haldia.length} grades</div>
              {Object.entries(stats.families).map(([k, n]) => (
                <div key={k} className="font-mono text-[10.5px]">
                  · {k}: {n}
                </div>
              ))}
            </div>
          </div>
        </div>
      </footer>

      {/* ============ TDS sheet modal ============ */}
      {sheetGrade && (
        <GradeSheet
          grade={sheetGrade}
          onClose={() => setSheetGrade(null)}
          onCompare={toggleCompare}
          onOpenGrade={openGrade}
          hideCompetitorRefs={view === "book"}
        />
      )}
    </div>
  );
}
