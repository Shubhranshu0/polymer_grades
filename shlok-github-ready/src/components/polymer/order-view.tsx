"use client";

import { useState } from "react";

const FORM_EMBED_URL =
  "https://docs.google.com/forms/d/e/1FAIpQLSfk4tN-iBhiqsYxd3Vl6xJMDFDRB0qODnlYxoZIm63M1i5JHg/viewform?embedded=true";
const FORM_TAB_URL = "https://forms.gle/hdUedQA3cQTnV7uU7";

const FORM_SECTIONS = [
  {
    title: "Business details",
    body: "Company / business name and address, your designation, GSTIN and trader licence number, and the delivery location.",
  },
  {
    title: "Material requirements",
    body: "Polymer family — HDPE, LLDPE, PP-Homo or PP-Co — the specific Halene grade you need, grade type (film, raffia, pipe, injection…) and the process you run.",
  },
  {
    title: "Consumption & supply",
    body: "Average monthly / annual consumption, your current supplier and the price you are paying, plus the payment terms you work on.",
  },
  {
    title: "Logistics & preference",
    body: "Required quantity and expected delivery date, freight arrangement (self or through us), trial quantities, and interest in a long-term Haldia MOU.",
  },
];

export function OrderView() {
  const [loaded, setLoaded] = useState(false);

  return (
    <div className="mx-auto max-w-3xl">
      {/* ============ heading ============ */}
      <div className="text-[10px] font-bold tracking-[0.3em] text-[#EA0C2F] uppercase">Polymer purchase</div>
      <h2 className="mt-1.5 font-serif text-2xl font-bold tracking-tight text-stone-900 sm:text-3xl">
        Place your order or enquiry
      </h2>
      <p className="mt-3 text-[13px] leading-relaxed text-stone-600">
        Fill in the order request below and we will contact you to go over details and availability before the order is
        completed. For faster service or direct information on current stock and pricing, call{" "}
        <a href="tel:+916370284496" className="font-mono font-bold whitespace-nowrap text-stone-900 hover:text-emerald-800">
          +91 63702 84496
        </a>{" "}
        or write to{" "}
        <a
          href="mailto:shubhranshu.dca.haldia@gmail.com"
          className="font-mono font-bold break-all text-stone-900 hover:text-emerald-800"
        >
          shubhranshu.dca.haldia@gmail.com
        </a>
        .
      </p>

      {/* ============ what the form covers ============ */}
      <div className="mt-6 grid gap-3 sm:grid-cols-2">
        {FORM_SECTIONS.map((s, i) => (
          <div key={s.title} className="border border-stone-200 bg-white px-4 py-4">
            <div className="flex items-baseline gap-2">
              <span className="font-mono text-[10px] font-bold text-stone-400">0{i + 1}</span>
              <span className="text-[11px] font-bold tracking-[0.14em] text-stone-800 uppercase">{s.title}</span>
            </div>
            <p className="mt-1.5 text-[11.5px] leading-relaxed text-stone-600">{s.body}</p>
          </div>
        ))}
      </div>

      {/* ============ embedded google form ============ */}
      <div className="mt-6 border border-stone-200 bg-white">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-stone-200 bg-stone-50 px-4 py-3">
          <div className="flex flex-wrap items-baseline gap-2">
            <span className="text-[9px] font-bold tracking-[0.22em] text-stone-400 uppercase">Order request form</span>
            <span className="font-mono text-[11px] font-bold text-stone-800">POLYMER PURCHASE</span>
          </div>
          <a
            href={FORM_TAB_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="text-[10px] font-bold tracking-widest whitespace-nowrap text-stone-500 uppercase hover:text-emerald-800"
          >
            Open in new tab ↗
          </a>
        </div>

        <div className="relative">
          <iframe
            src={FORM_EMBED_URL}
            title="SHLOK Polymers — polymer purchase order request form"
            className="block h-[9700px] w-full sm:h-[8600px]"
            onLoad={() => setLoaded(true)}
            loading="lazy"
          />
          {!loaded && (
            <div className="absolute inset-0 flex flex-col items-center justify-start gap-4 bg-white pt-20">
              <div className="h-10 w-10 animate-spin rounded-full border-[3px] border-stone-200 border-t-[#EA0C2F]" />
              <p className="font-mono text-xs tracking-[0.2em] text-stone-500 uppercase">Loading order form…</p>
              <a
                href={FORM_TAB_URL}
                target="_blank"
                rel="noopener noreferrer"
                className="text-[11px] font-bold text-emerald-800 underline"
              >
                Trouble loading? Open it in a new tab →
              </a>
            </div>
          )}
        </div>
      </div>

      <p className="mt-3 text-[11px] leading-relaxed text-stone-500">
        The form is hosted on Google Forms, in English with Hindi hints. Your responses are visible only to us and are used
        solely to prepare your quotation and order — nothing is shared with third parties.
      </p>
    </div>
  );
}
