export interface Property {
  name: string;
  test: string;
  unit: string;
  value: string;
}

export interface Processing {
  condition: string;
  window: string;
}

export interface KeyProp {
  value: string;
  unit: string;
  condition?: string;
}

export interface GradeKeyProps {
  mfi: KeyProp | null;
  density: KeyProp | null;
  tensile_yield: KeyProp | null;
  flexural: KeyProp | null;
  izod: KeyProp | null;
}

export interface PriceInfo {
  ex_works_min: number;
  ex_works_max: number;
  ex_works_ref: number;
  currency: string;
  effective: string;
}

export interface CompetitionInfo {
  key_props: string;
  superior: string;
  limitations: string;
  haldia_alt: string;
  comparison: string;
  reason_haldia_better: string;
  haldia_grade_superior: string;
  /** Resolved Haldia grade codes referenced by haldia_alt (primary matches) */
  alt_haldia_ids?: { grade: string; id: string }[];
  /** Extra Haldia grades referenced only inside comparison text */
  alt_haldia_secondary?: { grade: string; id: string }[];
  /** direct | closest | none */
  alt_match_kind?: string;
  /** Raw note when the match is a nearest-substitute rather than an equivalent */
  alt_note?: string;
  auto_mapped?: boolean;
}

export interface CompetedByRef {
  company: string;
  grade: string;
  id: string;
  polymer: string;
  /** direct | closest | secondary */
  kind: string;
}

export interface Grade {
  id: string;
  company: string;
  company_name: string;
  grade: string;
  polymer: string;
  polymer_label: string;
  family: string;
  segment: string;
  desc: string[];
  uses: string[];
  bis_code: string;
  key: GradeKeyProps;
  props: Property[];
  processing: Processing[];
  alt_codes?: string[];
  price?: PriceInfo;
  competition?: CompetitionInfo;
  /** Haldia grades only: competitor grades mapped against this grade */
  competed_by?: CompetedByRef[];
}

export interface PriceMatrixRow {
  location: string;
  prices: Record<string, string>;
}

export interface PriceSection {
  columns: string[][];
  matrix: PriceMatrixRow[];
  summary: Record<string, { min: number; max: number; ref: number }>;
}

export interface PriceDoc {
  circular: string;
  effective: string;
  HDPE?: Record<"ex_works" | "ex_stock", PriceSection>;
  LLDPE?: Record<"ex_works" | "ex_stock", PriceSection>;
  PP?: Record<"ex_works" | "ex_stock", PriceSection>;
}

export interface PriceAltRef {
  /** Display name (TDS name when the grade has a sheet) */
  grade: string;
  /** Dataset grade id when the alternative has a TDS sheet */
  id: string | null;
  /** competition = co-listed in the Polymer Competition mapping;
   *  price = identical price column in the HPL price list */
  src: "competition" | "price" | "both";
}

export interface PriceTableRow {
  grade: string;
  polymer: string;
  manufacturer: string;
  /** prime | br (blending resin) | og (off-grade) | powder */
  grade_type: string;
  /** Grade id in the TDS dataset, when the grade has a technical data sheet */
  tds_id: string | null;
  tds_grade: string | null;
  /** Ex-Stock Point basic price, Jharkhand_Ranchi price point (Rs./MT) */
  ex_stock_jh: number | null;
  /** Ex-Stock Point basic price, Bihar price point (Rs./MT) */
  ex_stock_br: number | null;
  /** Ex-Plant / Ex-Works basic price, Jharkhand_Ranchi price point (Rs./MT) */
  ex_ware_jh: number | null;
  /** Ex-Plant / Ex-Works basic price, Bihar price point (Rs./MT) */
  ex_ware_br: number | null;
  alts: PriceAltRef[];
}

export interface PriceTableMeta {
  manufacturer: string;
  pe_circular: string;
  pe_effective: string;
  pp_circular: string;
  pp_effective: string;
  unit: string;
  period_label: string;
  ex_stock_basis: string;
  ex_warehouse_basis: string;
  sources: string[];
  generated: string;
}

export interface PriceTable {
  meta: PriceTableMeta;
  rows: PriceTableRow[];
}

export interface Dataset {
  meta: {
    generated: string;
    source_pdfs: string[];
    total_grades: number;
    grade_counts: Record<string, Record<string, number>>;
  };
  companies: Record<string, {
    name: string;
    short: string;
    city: string;
    brands: string[];
    color: string;
    note: string;
  }>;
  polymer_labels: Record<string, string>;
  grades: Grade[];
  /** September 2026 HPL circular metadata (full matrices replaced by price_table) */
  prices: { pe: { circular: string; effective: string }; pp: { circular: string; effective: string } };
  /** Consolidated Haldia-only price table for the Pricing page */
  price_table: PriceTable;
  competition_notes: string[];
}

export const POLYMER_ORDER = [
  "HDPE",
  "LLDPE",
  "LDPE",
  "PP",
  "PP-Homo",
  "PP-Random",
  "PP-Impact",
] as const;

export const POLYMER_COLORS: Record<string, string> = {
  HDPE: "#1e5f8a",
  LLDPE: "#0d7d6e",
  LDPE: "#a16207",
  PP: "#93336f",
  "PP-Homo": "#93336f",
  "PP-Random": "#7c3aed",
  "PP-Impact": "#be3455",
};

export const COMPANY_STYLES: Record<string, { color: string; bg: string; label: string }> = {
  haldia: { color: "#C8102E", bg: "#fdf2f3", label: "HPL" },
  reliance: { color: "#0F4C81", bg: "#eff5fa", label: "RIL" },
  iocl: { color: "#d9631e", bg: "#fdf3ec", label: "IOCL" },
  ongc: { color: "#2E7D32", bg: "#f0f7f0", label: "OPaL" },
};
