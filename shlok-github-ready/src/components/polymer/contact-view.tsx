"use client";

const CONTACT = {
  name: "Shubhranshu",
  role: "Polymer Engineer · Haldia Polymers — Jharkhand & Bihar",
  email: "shubhranshu.dca.haldia@gmail.com",
  phone: "6370284496",
  phoneIntl: "+916370284496",
  linkedin: "www.linkedin.com/in/shubhranshu-polymer-engineer",
  linkedinUrl: "https://www.linkedin.com/in/shubhranshu-polymer-engineer",
};

export function ContactView({ onGoOrder }: { onGoOrder?: () => void }) {
  return (
    <div className="mx-auto max-w-3xl">
      <div className="text-[10px] font-bold tracking-[0.3em] text-[#EA0C2F] uppercase">Contact us</div>
      <h2 className="mt-1.5 font-serif text-2xl font-bold tracking-tight text-stone-900 sm:text-3xl">
        Talk polymers with us
      </h2>
      <p className="mt-3 text-[13px] leading-relaxed text-stone-600">
        For Haldia (Halene) polymer supply across Jharkhand and Bihar, grade selection against Reliance,
        IOCL and OPaL equivalents, current prices or technical data clarifications — reach out directly.
      </p>

      {/* purchase enquiry banner */}
      <div className="mt-6 border border-[#EA0C2F] bg-[#EA0C2F] px-5 py-4 text-white">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="min-w-0">
            <div className="text-[9px] font-bold tracking-[0.22em] text-white/80 uppercase">Purchase enquiry</div>
            <p className="mt-1 max-w-xl text-[12.5px] leading-relaxed text-white">
              Looking to buy? Place your order or enquiry through the <b>POLYMER PURCHASE</b> form — grades, quantities,
              delivery and payment terms, all in one place.
            </p>
          </div>
          {onGoOrder && (
            <button
              onClick={onGoOrder}
              className="shrink-0 border border-white/50 px-4 py-2 text-[10px] font-bold tracking-widest whitespace-nowrap uppercase transition-colors hover:bg-white hover:text-[#EA0C2F]"
            >
              Open order form →
            </button>
          )}
        </div>
      </div>

      <div className="mt-6 grid gap-3 sm:grid-cols-3">
        {/* email */}
        <a
          href={`mailto:${CONTACT.email}`}
          className="group border border-stone-200 bg-white px-4 py-5 transition-colors hover:border-emerald-600"
        >
          <div className="text-[9px] font-bold tracking-[0.22em] text-stone-400 uppercase">E-mail</div>
          <div className="mt-2 font-mono text-[12px] font-bold break-all text-stone-900 group-hover:text-emerald-800">
            {CONTACT.email}
          </div>
          <div className="mt-2 text-[11px] text-stone-500 group-hover:text-emerald-700">
            Write to us →
          </div>
        </a>

        {/* phone */}
        <a
          href={`tel:${CONTACT.phoneIntl}`}
          className="group border border-stone-200 bg-white px-4 py-5 transition-colors hover:border-emerald-600"
        >
          <div className="text-[9px] font-bold tracking-[0.22em] text-stone-400 uppercase">Phone</div>
          <div className="mt-2 font-mono text-[17px] font-bold text-stone-900 group-hover:text-emerald-800">
            {CONTACT.phone}
          </div>
          <div className="mt-2 text-[11px] text-stone-500 group-hover:text-emerald-700">Call us →</div>
        </a>

        {/* linkedin */}
        <a
          href={CONTACT.linkedinUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="group border border-stone-200 bg-white px-4 py-5 transition-colors hover:border-emerald-600"
        >
          <div className="text-[9px] font-bold tracking-[0.22em] text-stone-400 uppercase">LinkedIn</div>
          <div className="mt-2 font-mono text-[12px] font-bold break-all text-stone-900 group-hover:text-emerald-800">
            {CONTACT.linkedin}
          </div>
          <div className="mt-2 text-[11px] text-stone-500 group-hover:text-emerald-700">
            Connect with me →
          </div>
        </a>
      </div>

      <div className="mt-6 border border-stone-200 bg-stone-50 px-5 py-4">
        <div className="text-[9px] font-bold tracking-[0.22em] text-stone-400 uppercase">
          Service territory
        </div>
        <p className="mt-1.5 text-[12px] leading-relaxed text-stone-600">
          Halene HDPE, LLDPE and PP grades for all districts of <b>Jharkhand</b> and <b>Bihar</b> — ex-stock
          and ex-warehouse basis. Grade recommendations, TDS comparisons and competitor cross-references are
          always free.
        </p>
      </div>
    </div>
  );
}
