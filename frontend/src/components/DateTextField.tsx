"use client";

import { TextField, type TextFieldProps } from "@mui/material";

export const DATE_PLACEHOLDER = "DD-MM-YYYY";
export const DATE_HELPER = "DD-MM-YYYY";

/** True when both dates are set and the end is before the start. */
export function endBeforeStart(start: unknown, end: unknown) {
  const a = String(start || "").slice(0, 10);
  const b = String(end || "").slice(0, 10);
  if (!/^\d{4}-\d{2}-\d{2}$/.test(a) || !/^\d{4}-\d{2}-\d{2}$/.test(b)) return false;
  return b < a;
}

/** Later date cannot fall before the earlier one. Label is the later field. */
export const DATE_ORDER: [string, string, string][] = [
  ["start_date", "end_date", "End date"],
  ["start_date", "maturity_date", "Comes back on"],
  ["review_period_start", "review_period_end", "Period end"],
  ["invoice_date", "due_date", "Due date"],
  ["period_start", "period_end", "Period end"],
  ["quote_date", "valid_until", "Valid until"],
  ["rfq_date", "valid_until", "Valid until"],
  ["order_date", "expected_date", "Expected date"],
  ["request_date", "required_date", "Required by"],
  ["valid_from", "valid_until", "Valid until"],
  ["issued_on", "expires_on", "Expires on"],
  ["purchase_date", "disposal_date", "Disposal date"],
];

export function dateOrderIssue(values: Record<string, unknown>, endKey?: string) {
  for (const [startKey, laterKey, label] of DATE_ORDER) {
    if (endKey && laterKey !== endKey) continue;
    if (endBeforeStart(values[startKey], values[laterKey])) {
      return { endKey: laterKey, message: `${label} cannot be before the start date.` };
    }
  }
  if (Array.isArray(values.items)) {
    for (const row of values.items) {
      if (!row || typeof row !== "object") continue;
      const item = row as Record<string, unknown>;
      if (endBeforeStart(item.valid_from, item.valid_until)) {
        return { endKey: "valid_until", message: "Valid until cannot be before the start date." };
      }
    }
  }
  return null;
}

type Props = Omit<TextFieldProps, "type"> & {
  /** Show format helper under the field (default true when empty helperText). */
  showFormatHint?: boolean;
  /** Earliest date the picker accepts (YYYY-MM-DD). */
  notBefore?: string;
};

/** Consistent date input UX across the app. */
export default function DateTextField({
  showFormatHint = true,
  helperText,
  notBefore,
  error,
  slotProps,
  sx,
  value,
  ...rest
}: Props) {
  const tooEarly = endBeforeStart(notBefore, value);
  const hint = tooEarly
    ? "Cannot be before the start date."
    : (helperText ?? (showFormatHint ? DATE_HELPER : undefined));
  const extra = (slotProps || {}) as {
    inputLabel?: Record<string, unknown>;
    htmlInput?: Record<string, unknown>;
  };
  const min = String(notBefore || "").slice(0, 10);

  return (
    <TextField
      {...rest}
      value={value}
      type="date"
      error={error || tooEarly}
      helperText={hint}
      fullWidth={rest.fullWidth ?? true}
      sx={[
        {
          "& .MuiInputBase-input": {
            paddingTop: "18px",
            paddingBottom: "10px",
          },
        },
        ...(Array.isArray(sx) ? sx : sx ? [sx] : []),
      ]}
      slotProps={{
        ...extra,
        inputLabel: { shrink: true, ...extra.inputLabel },
        htmlInput: { ...extra.htmlInput, ...(min ? { min } : {}) },
      }}
    />
  );
}

/** Local calendar date as YYYY-MM-DD (not UTC — avoids off-by-one in PK/UAE). */
export function todayISO(): string {
  const d = new Date();
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

/** Add calendar months to an ISO date string. */
export function addMonthsISO(iso: string, months: number): string {
  if (!iso) return "";
  const d = new Date(`${iso}T12:00:00`);
  if (Number.isNaN(d.getTime())) return "";
  d.setMonth(d.getMonth() + months);
  return d.toISOString().slice(0, 10);
}

/** Inclusive day count between two ISO dates. */
export function daysInclusive(from: string, to: string): number {
  if (!from || !to) return 0;
  const a = new Date(`${from}T12:00:00`);
  const b = new Date(`${to}T12:00:00`);
  if (Number.isNaN(a.getTime()) || Number.isNaN(b.getTime()) || b < a) return 0;
  return Math.floor((b.getTime() - a.getTime()) / 86400000) + 1;
}
