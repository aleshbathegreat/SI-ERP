import { suggestDocNo } from "@/lib/docNumbers";
import { todayISO } from "@/components/DateTextField";

/** Document fields that always auto-number on create when blank. */
export const AUTO_NUMBER_FIELDS: Record<string, string> = {
  invoice_no: "AP",
  po_no: "PO",
  order_no: "SO",
  loan_number: "LN",
  challan_no: "CH",
  asset_code: "FA",
};

/** Opt-in via FieldDef.autoGenerate. Generic `code` is assigned by the server. */
export const OPT_IN_NUMBER_FIELDS: Record<string, string> = {
  sku: "SKU",
};

/** @deprecated Prefer type:"date" — all date fields now default to today. */
export const DEFAULT_TODAY_DATES = new Set<string>();

export function applyCreateDefaults(
  empty: Record<string, unknown>,
  fields: { name: string; type?: string; autoGenerate?: boolean }[]
): Record<string, unknown> {
  const out = { ...empty };
  const today = todayISO();

  for (const [name, prefix] of Object.entries(AUTO_NUMBER_FIELDS)) {
    if (name in out && (out[name] === "" || out[name] == null)) {
      out[name] = suggestDocNo(prefix);
    }
  }

  for (const f of fields || []) {
    if (!f.autoGenerate) continue;
    const prefix = OPT_IN_NUMBER_FIELDS[f.name] || AUTO_NUMBER_FIELDS[f.name];
    if (!prefix) continue;
    if (out[f.name] === "" || out[f.name] == null) {
      out[f.name] = suggestDocNo(prefix);
    }
  }

  // Only skip personal/historical dates that must never auto-fill as "today".
  const skipToday = (name: string) =>
    /birth|dob|date_of_birth|anniversary/i.test(name);

  // Best practice: document/txn dates default to today on create.
  // Skip birth/expiry-style fields (user must choose deliberately).
  for (const f of fields || []) {
    if (f.type !== "date") continue;
    if (skipToday(f.name)) continue;
    if (out[f.name] === "" || out[f.name] == null || !(f.name in out)) {
      out[f.name] = today;
    }
  }
  for (const [name, val] of Object.entries(out)) {
    if (val !== "" && val != null) continue;
    if (skipToday(name)) continue;
    if (/(^|_)(date|on)$/i.test(name) || /_date$/i.test(name)) {
      out[name] = today;
    }
  }
  return out;
}
