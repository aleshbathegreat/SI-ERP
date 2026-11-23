/** Accountant-facing labels for Finance (Pakistan / IFRS-friendly). */

export const TAX_TYPE_LABELS: Record<string, string> = {
  wht: "WHT (Withholding)",
  sales_tax: "Sales tax",
  income_tax: "Income tax",
  other: "Other",
};

export function taxTypeLabel(value?: string | null): string {
  if (!value) return "—";
  return TAX_TYPE_LABELS[value] || value;
}

export const INVOICE_STATUS_LABELS: Record<string, string> = {
  draft: "Draft",
  submitted: "Submitted",
  approved: "Approved",
  paid: "Paid",
  rejected: "Rejected",
};

export const JOURNAL_STATUS_LABELS: Record<string, string> = {
  draft: "Draft",
  submitted: "Submitted",
  approved: "Approved",
  posted: "Posted to GL",
  rejected: "Rejected",
};

export function humanizeStatus(value?: string | null): string {
  if (!value) return "—";
  return (
    INVOICE_STATUS_LABELS[value] ||
    JOURNAL_STATUS_LABELS[value] ||
    value.replace(/_/g, " ")
  );
}
