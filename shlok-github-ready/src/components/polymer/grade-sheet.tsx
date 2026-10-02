"use client";

import { Grade } from "@/lib/polymer-types";
import { COMPANY_STYLES, POLYMER_COLORS } from "@/lib/polymer-types";

export function GradeSheet({
  grade,
  onClose,
  onCompare,
  onOpenGrade,
  hideCompetitorRefs = false,
}: {
  grade: Grade;
  onClose: () => void;
  onCompare: (g: Grade) => void;
  onOpenGrade: (g: Grade) => void;
  /** Grade Book context: hide cross-producer references on Haldia sheets */
  hideCompetitorRefs?: boolean;
}) {
  const comp = COMPANY_STYLES[grade.company] ?? { color: "#555", bg: "#f5f5f5", label: "?" };
  const polyColor = POLYMER_COLORS[grade.polymer] ?? "#555";
  const c = grade.competition;

  const findHaldiaGrade = (name: string): Grade | null => {
    if (!name || name === "N/A") return null;
    const clean = name.replace(/[^A-Za-z0-9]/g, "").toUpperCase();
    return (
      haldiaGradesCache.find(
        (g) => g.grade.replace(/[^A-Za-z0-9]/g, "").toUpperCase() === clean
      ) ?? null
    );
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-stone-950/60 p-0 backdrop-blur-[2px] sm:p-6"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label={`Technical data sheet ${grade.grade}`}
    >
      <div
        className="relative my-0 w-full max-w-4xl border border-stone-300 bg-white shadow-2xl sm:my-4"
        onClick={(e) => e.stopPropagation()}
      >
        {/* header band */}
        <header className="sticky top-0 z-10 border-b border-stone-200 bg-white/95 px-5 py-4 backdrop-blur sm:px-8">
          <div className="flex items-start justify-between gap-4">
            <div className="min-w-0">
              <div
                className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[10px] font-bold tracking-[0.16em] uppercase"
                style={{ color: comp.color }}
              >
                <span className="inline-flex items-center gap-1.5">
                  <span className="inline-block h-1.5 w-1.5 rounded-full" style={{ background: comp.color }} />
                  {grade.company_name}
                </span>
                <span className="text-stone-400">{grade.family}</span>
                <span style={{ color: polyColor }}>{grade.polymer_label}</span>
              </div>
              <h2 className="mt-1 font-mono text-3xl font-bold tracking-tight text-stone-900">{grade.grade}</h2>
              <div className="mt-0.5 text-sm font-semibold" style={{ color: polyColor }}>
                {grade.segment}
              </div>
            </div>
            <div className="flex shrink-0 items-center gap-2">
              <button
                onClick={() => onCompare(grade)}
                className="hidden rounded-sm border border-stone-300 px-3 py-1.5 text-[11px] font-bold tracking-widest text-stone-700 uppercase hover:border-stone-600 hover:text-stone-950 sm:block"
              >
                + Compare
              </button>
              <button
                onClick={onClose}
                aria-label="Close"
                className="flex h-8 w-8 items-center justify-center rounded-full border border-stone-300 text-lg leading-none text-stone-600 hover:border-stone-600 hover:text-stone-950"
              >
                ×
              </button>
            </div>
          </div>
        </header>

        <div className="px-5 py-6 sm:px-8">
          {/* description */}
          {grade.desc.length > 0 && (
            <section className="mb-6">
              <SectionTitle>Product description</SectionTitle>
              <div className="space-y-2 text-sm leading-relaxed text-stone-700">
                {grade.desc.map((d, i) => (
                  <p key={i}>{d}</p>
                ))}
              </div>
            </section>
          )}

          {/* BIS + key stats band */}
          <div className="mb-6 grid gap-px overflow-hidden border border-stone-200 bg-stone-200 sm:grid-cols-4">
            <StatCell label="MFI" value={grade.key.mfi ? `${grade.key.mfi.value} ${grade.key.mfi.unit}` : "—"} sub={grade.key.mfi?.condition ?? ""} />
            <StatCell label="Density" value={grade.key.density ? `${grade.key.density.value} ${grade.key.density.unit}` : "—"} sub="23°C" />
            <StatCell label="Tensile @ Yield" value={grade.key.tensile_yield ? `${grade.key.tensile_yield.value} ${grade.key.tensile_yield.unit}` : "—"} sub="ASTM D638" />
            <StatCell
              label="BIS Designation"
              value={grade.bis_code || "—"}
              sub={grade.alt_codes?.length ? `also coded ${grade.alt_codes.join(", ")}` : "IS designation code"}
              mono
            />
          </div>

          {/* property table */}
          <section className="mb-6">
            <SectionTitle>Typical properties</SectionTitle>
            {grade.props.length === 0 ? (
              <p className="text-sm text-stone-500">No properties published.</p>
            ) : (
              <div className="overflow-x-auto border border-stone-200">
                <table className="w-full min-w-[560px] border-collapse text-left text-[13px]">
                  <thead>
                    <tr className="bg-stone-100 text-[10px] font-bold tracking-[0.14em] text-stone-500 uppercase">
                      <th className="px-3 py-2.5">Property</th>
                      <th className="px-3 py-2.5">Test method</th>
                      <th className="px-3 py-2.5">Unit</th>
                      <th className="px-3 py-2.5 text-right">Nominal value</th>
                    </tr>
                  </thead>
                  <tbody>
                    {grade.props.map((p, i) => (
                      <tr key={i} className="border-t border-stone-100 odd:bg-white even:bg-stone-50/60">
                        <td className="px-3 py-2 font-medium text-stone-800">{p.name}</td>
                        <td className="px-3 py-2 text-stone-500">{p.test || "—"}</td>
                        <td className="px-3 py-2 font-mono text-stone-500">{p.unit || "—"}</td>
                        <td className="px-3 py-2 text-right font-mono font-bold text-stone-900">{p.value || "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          {/* processing */}
          {grade.processing.length > 0 && (
            <section className="mb-6">
              <SectionTitle>Suggested processing window</SectionTitle>
              <div className="grid gap-px overflow-hidden border border-stone-200 bg-stone-200 sm:grid-cols-2 lg:grid-cols-3">
                {grade.processing.map((p, i) => (
                  <div key={i} className="bg-white px-4 py-3">
                    <div className="text-[9px] font-bold tracking-[0.18em] text-stone-400 uppercase">{p.condition}</div>
                    <div className="mt-1 font-mono text-sm font-bold text-stone-900">{p.window}</div>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* applications */}
          {grade.uses.length > 0 && (
            <section className="mb-6">
              <SectionTitle>Applications</SectionTitle>
              <ul className="grid gap-1.5 sm:grid-cols-2">
                {grade.uses.map((u, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-stone-700">
                    <span className="mt-[7px] inline-block h-1 w-1 shrink-0 rounded-full" style={{ background: comp.color }} />
                    {u}
                  </li>
                ))}
              </ul>
            </section>
          )}

          {/* competing grades (Haldia sheets — hidden in Grade Book context) */}
          {grade.company === "haldia" && !hideCompetitorRefs && (grade.competed_by?.length ?? 0) > 0 && (
            <section className="mb-6">
              <SectionTitle accent="#C8102E">Competing grades across producers</SectionTitle>
              <p className="mb-3 text-xs leading-relaxed text-stone-500">
                Competitor grades whose alternate-Haldia mapping points at this grade (per the competition sheet).
                Click a code to open its data sheet.
              </p>
              <div className="flex flex-wrap gap-1.5">
                {(grade.competed_by ?? []).map((c, i) => {
                  const cc = COMPANY_STYLES[c.company] ?? { color: "#555", bg: "#f5f5f5", label: c.company };
                  return (
                    <button
                      key={`${c.id}-${i}`}
                      onClick={() => {
                        const cg = getGradeById(c.id);
                        if (cg) onOpenGrade(cg);
                      }}
                      title={`${cc.label} · ${c.polymer}${c.kind === "closest" ? " · nearest-substitute mapping" : c.kind === "secondary" ? " · referenced in comparison notes" : ""}`}
                      className="inline-flex items-center gap-1.5 border px-2 py-1 font-mono text-xs font-bold transition-colors hover:bg-stone-900 hover:text-white"
                      style={{ borderColor: cc.color, color: cc.color, background: cc.bg }}
                    >
                      {c.grade}
                      <span className="text-[9px] font-bold tracking-wider opacity-70">{cc.label}</span>
                      {c.kind === "closest" && <span className="text-[10px] opacity-70">~</span>}
                    </button>
                  );
                })}
              </div>
            </section>
          )}

          {/* price */}
          {grade.price && (
            <section className="mb-6">
              <SectionTitle>{pricePeriodLabel(grade.price.effective)} price indication</SectionTitle>
              <div className="flex flex-wrap items-end gap-x-8 gap-y-3 border border-emerald-200 bg-emerald-50/60 px-5 py-4">
                <div>
                  <div className="text-[9px] font-bold tracking-[0.18em] text-emerald-700 uppercase">Ex-works reference</div>
                  <div className="font-mono text-2xl font-bold text-emerald-900">
                    ₹ {grade.price.ex_works_ref.toLocaleString("en-IN")}
                    <span className="ml-1 text-xs font-semibold text-emerald-700">/MT</span>
                  </div>
                </div>
                <div>
                  <div className="text-[9px] font-bold tracking-[0.18em] text-emerald-700 uppercase">Range across India</div>
                  <div className="font-mono text-sm font-bold text-emerald-900">
                    ₹ {grade.price.ex_works_min.toLocaleString("en-IN")} – {grade.price.ex_works_max.toLocaleString("en-IN")}
                  </div>
                </div>
                <div className="text-[11px] text-emerald-800/70">
                  HPL price circular · effective {grade.price.effective}
                </div>
              </div>
            </section>
          )}

          {/* competition analysis */}
          {c && (c.haldia_alt || c.comparison || c.reason_haldia_better) && (
            <section className="mb-2">
              <SectionTitle accent={comp.color}>Competitive positioning vs Haldia</SectionTitle>
              <div className="grid gap-4 lg:grid-cols-2">
                <InfoCard title="Alternate Haldia grade(s)" accent="#C8102E">
                  <div className="flex flex-wrap gap-1.5">
                    {(c.alt_haldia_ids ?? []).length > 0 ? (
                      (c.alt_haldia_ids ?? []).map((a) => {
                        const hg = findHaldiaGrade(a.grade);
                        return hg ? (
                          <button
                            key={a.id}
                            onClick={() => onOpenGrade(hg)}
                            title={`Open Haldia ${a.grade} data sheet`}
                            className="border border-[#C8102E]/40 bg-[#fdf2f3] px-2 py-1 font-mono text-xs font-bold text-[#C8102E] transition-colors hover:border-[#C8102E] hover:bg-[#C8102E] hover:text-white"
                          >
                            {a.grade} — open sheet →
                          </button>
                        ) : (
                          <span key={a.id} className="border border-stone-200 px-2 py-1 font-mono text-xs text-stone-600">
                            {a.grade}
                          </span>
                        );
                      })
                    ) : (
                      <span className="font-mono text-sm">{c.haldia_alt || "N/A"}</span>
                    )}
                  </div>
                  {(c.alt_haldia_secondary ?? []).length > 0 && (
                    <p className="mt-2 text-[11px] text-stone-500">
                      Also referenced: {c.alt_haldia_secondary!.map((s) => s.grade).join(", ")}
                    </p>
                  )}
                  {c.alt_match_kind === "closest" && c.alt_note && (
                    <p className="mt-2 text-[11px] leading-relaxed text-amber-800">
                      <span className="font-bold uppercase">Nearest substitute · </span>
                      {c.alt_note}
                    </p>
                  )}
                  {c.auto_mapped && (
                    <p className="mt-2 text-[11px] leading-relaxed text-amber-800">
                      <span className="font-bold uppercase">Auto-mapped · </span>
                      closest Haldia grade by TDS profile — this grade is not present in the uploaded competition sheet.
                    </p>
                  )}
                  {c.haldia_grade_superior && (
                    <p className="mt-2 text-xs leading-relaxed text-stone-600">{c.haldia_grade_superior}</p>
                  )}
                </InfoCard>
                <InfoCard title="Why the Haldia grade is stronger" accent="#C8102E">
                  <p className="text-xs leading-relaxed whitespace-pre-line text-stone-700">
                    {c.reason_haldia_better || c.comparison || "—"}
                  </p>
                </InfoCard>
                {c.key_props && (
                  <InfoCard title="Competitor key properties">
                    <p className="text-xs leading-relaxed whitespace-pre-line text-stone-700">{c.key_props}</p>
                  </InfoCard>
                )}
                {c.limitations && (
                  <InfoCard title="Competitor limitations">
                    <p className="text-xs leading-relaxed whitespace-pre-line text-stone-700">{c.limitations}</p>
                  </InfoCard>
                )}
              </div>
            </section>
          )}
        </div>
      </div>
    </div>
  );
}

const PRICE_MONTHS = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

function pricePeriodLabel(effective?: string): string {
  const m = /^(\d{2})\.(\d{2})\.(\d{4})$/.exec(effective ?? "");
  if (!m) return "Current";
  return `${PRICE_MONTHS[parseInt(m[2], 10) - 1]} ${m[3]}`;
}

function SectionTitle({ children, accent }: { children: React.ReactNode; accent?: string }) {
  return (
    <h3
      className="mb-3 flex items-center gap-2 text-[11px] font-bold tracking-[0.22em] uppercase"
      style={{ color: accent ?? "#57534e" }}
    >
      <span className="inline-block h-2 w-2" style={{ background: accent ?? "#57534e" }} />
      {children}
    </h3>
  );
}

function StatCell({ label, value, sub, mono }: { label: string; value: string; sub?: string; mono?: boolean }) {
  return (
    <div className="bg-white px-4 py-3">
      <div className="text-[9px] font-bold tracking-[0.18em] text-stone-400 uppercase">{label}</div>
      <div className={`mt-1 text-sm font-bold text-stone-900 ${mono ? "font-mono text-xs" : ""}`}>{value}</div>
      {sub && <div className="mt-0.5 truncate text-[10px] text-stone-500">{sub}</div>}
    </div>
  );
}

function InfoCard({ title, children, accent }: { title: string; children: React.ReactNode; accent?: string }) {
  return (
    <div className="border border-stone-200 bg-stone-50/60 px-4 py-3">
      <div className="mb-1.5 text-[9px] font-bold tracking-[0.18em] uppercase" style={{ color: accent ?? "#78716c" }}>
        {title}
      </div>
      {children}
    </div>
  );
}

// cache for cross-linking haldia grades
import { Grade as G } from "@/lib/polymer-types";
let haldiaGradesCache: G[] = [];
export function setHaldiaGradesCache(gs: G[]) {
  haldiaGradesCache = gs;
}
export function getHaldiaGradeById(id: string): G | null {
  return haldiaGradesCache.find((g) => g.id === id) ?? null;
}
let allGradesCache: G[] = [];
export function setAllGradesCache(gs: G[]) {
  allGradesCache = gs;
}
export function getGradeById(id: string): G | null {
  return allGradesCache.find((g) => g.id === id) ?? null;
}
