import api from "@/lib/api";

export type ItemLabel = {
  id: number;
  barcode: string;
  name: string;
  sku: string;
  unit?: string;
  sales_price?: string;
};

export function qrImageSrc(payload: string, size = 160) {
  return `https://api.qrserver.com/v1/create-qr-code/?size=${size}x${size}&data=${encodeURIComponent(
    payload
  )}`;
}

export async function fetchItemLabel(id: number | string): Promise<ItemLabel> {
  const { data } = await api.get<ItemLabel>(`/inventory/items/${id}/label/`);
  return data;
}

const esc = (s: string) =>
  s.replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c] as string
  );

/** Open a minimal printable label (QR + name/SKU/barcode) in a new window. */
export async function printItemLabel(id: number | string) {
  const label = await fetchItemLabel(id);
  const w = window.open("", "_blank", "width=420,height=420");
  if (!w) throw new Error("Pop-up blocked — allow pop-ups to print labels.");
  w.document.write(`<!doctype html><html><head><title>Label ${esc(label.sku)}</title>
<style>
  body{font-family:Arial,sans-serif;margin:0;padding:12px}
  .label{width:300px;border:1px dashed #999;padding:10px;text-align:center}
  .name{font-weight:700;font-size:14px;margin-bottom:4px}
  .sku{font-size:12px}
  .code{font-family:monospace;font-size:16px;letter-spacing:2px;margin-top:6px}
  @media print{.label{border:none}}
</style></head><body>
<div class="label">
  <div class="name">${esc(label.name)}</div>
  <div class="sku">SKU: ${esc(label.sku)}</div>
  <img src="${qrImageSrc(label.barcode, 140)}" width="140" height="140" alt="QR" />
  <div class="code">${esc(label.barcode)}</div>
</div>
<script>window.onload=function(){setTimeout(function(){window.print()},400)}</script>
</body></html>`);
  w.document.close();
}
