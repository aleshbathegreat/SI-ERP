export const CURRENCY_OPTIONS = [
  { value: "PKR", label: "PKR — Pakistani Rupee" },
  { value: "USD", label: "USD — US Dollar" },
  { value: "EUR", label: "EUR — Euro" },
  { value: "GBP", label: "GBP — British Pound" },
  { value: "AED", label: "AED — UAE Dirham" },
  { value: "SAR", label: "SAR — Saudi Riyal" },
  { value: "CNY", label: "CNY — Chinese Yuan" },
  { value: "INR", label: "INR — Indian Rupee" },
] as const;

export type CurrencyCode = (typeof CURRENCY_OPTIONS)[number]["value"];

export function normalizeCurrency(code?: string | null, fallback = "PKR"): string {
  const c = String(code || fallback).trim().toUpperCase();
  return c.length === 3 ? c : fallback;
}
