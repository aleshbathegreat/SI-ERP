function fold(value: unknown) {
  return String(value ?? "")
    .trim()
    .toLowerCase()
    .replace(/[\s_-]+/g, "");
}

/** "expense — Expense" becomes "Expense". Distinct codes stay, e.g. "1100 — Cash". */
export function codeNameLabel(code: unknown, name: unknown, fallback: unknown = ""): string {
  const c = String(code ?? "").trim();
  const n = String(name ?? "").trim();
  if (!n) return c || String(fallback ?? "");
  if (!c || fold(c) === fold(n)) return n;
  return `${c} — ${n}`;
}

export function sameToken(a: unknown, b: unknown) {
  const left = fold(a);
  const right = fold(b);
  return Boolean(left) && left === right;
}

/** Drop repeated words such as "expense — Expense (expense)". */
export function distinctLabel(...parts: unknown[]) {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const part of parts) {
    let text = String(part ?? "").trim();
    if (!text) continue;
    text = text
      .replace(/\s*\(([^)]+)\)/g, (match, inner) => (seen.has(fold(inner)) || fold(inner) === fold(text) ? "" : match))
      .replace(/\s{2,}/g, " ")
      .trim();
    const key = fold(text);
    if (!text || seen.has(key)) continue;
    seen.add(key);
    out.push(text);
  }
  return out.join(" — ");
}
