/** Shared limits for number inputs. Signed balances are listed by name. */

const YEAR_MIN = 2000;
const YEAR_MAX = 2100;

const YEAR_FIELDS = new Set(["fiscal_year", "year", "period_year"]);
const MONTH_FIELDS = new Set(["month", "period_month"]);
const SIGNED_FIELDS = new Set([
  "statement_balance",
  "book_balance",
  "opening_balance",
  "current_balance",
  "net_payable",
]);
const PERCENT_FIELDS = new Set([
  "rate_percent",
  "income_tax_rate",
  "provident_fund_rate",
  "employer_pf_rate",
  "depreciation_rate",
  "probability",
]);

export type NumberBounds = { min?: number; max?: number };

export function numberBounds(
  name: string,
  min?: number,
  max?: number
): NumberBounds {
  if (min != null || max != null) return { min, max };
  if (YEAR_FIELDS.has(name)) return { min: YEAR_MIN, max: YEAR_MAX };
  if (MONTH_FIELDS.has(name)) return { min: 1, max: 12 };
  if (SIGNED_FIELDS.has(name)) return {};
  if (PERCENT_FIELDS.has(name)) return { min: 0, max: 100 };
  if (name === "port") return { min: 1, max: 65535 };
  return { min: 0 };
}

export function yearHint(name: string, helperText?: string) {
  if (helperText) return helperText;
  if (YEAR_FIELDS.has(name)) return `${YEAR_MIN}–${YEAR_MAX}`;
  if (MONTH_FIELDS.has(name)) return "1–12";
  if (PERCENT_FIELDS.has(name)) return "0–100";
  return helperText;
}

/** Drop a negative keystroke when the field cannot be negative. */
export function rejectNegative(raw: string, bounds: NumberBounds): string | null {
  if (bounds.min == null || bounds.min < 0) return raw;
  if (raw === "" || raw === "-" || raw.startsWith("-")) return raw === "" ? "" : null;
  return raw;
}

export function snapNumber(value: unknown, bounds: NumberBounds): number | "" | null {
  if (value === "" || value == null) return "";
  const n = Number(value);
  if (Number.isNaN(n)) return null;
  let next = n;
  if (bounds.min != null && next < bounds.min) next = bounds.min;
  if (bounds.max != null && next > bounds.max) next = bounds.max;
  return next;
}
