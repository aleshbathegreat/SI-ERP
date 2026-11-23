/** Client-side document number suggestions (server re-validates uniqueness). */

export function suggestDocNo(prefix: string): string {
  const year = new Date().getFullYear();
  const seq = String(Date.now()).slice(-5);
  return `${prefix.toUpperCase()}-${year}-${seq}`;
}

export function addDaysISO(iso: string, days: number): string {
  if (!iso) return "";
  const d = new Date(`${iso}T12:00:00`);
  if (Number.isNaN(d.getTime())) return "";
  d.setDate(d.getDate() + days);
  return d.toISOString().slice(0, 10);
}
