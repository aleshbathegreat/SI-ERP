"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Box,
  Button,
  Chip,
  IconButton,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import DateTextField, { todayISO } from "@/components/DateTextField";
import AddIcon from "@mui/icons-material/Add";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutlined";
import EditIcon from "@mui/icons-material/Edit";
import { useParams } from "next/navigation";
import { useSnackbar } from "notistack";
import FormPageShell from "@/components/crud/FormPageShell";
import { DetailSection } from "@/components/crud/DetailPageShell";
import RelationSelect, { RELATIONS } from "@/components/crud/RelationSelect";
import ModuleGate from "@/components/ModuleGate";
import { useEntityForm, type FormMode } from "@/hooks/useEntityForm";
import { usePermissions } from "@/hooks/usePermissions";
import api from "@/lib/api";
import { errorSnackbarOpts, getApiErrorMessage } from "@/lib/apiError";
import { formatMoney } from "@/lib/format";

type Line = {
  item: string;
  description: string;
  qty: string;
  unit_price: string;
};

const emptyLine = (): Line => ({ item: "", description: "", qty: "1", unit_price: "0" });
const moduleKey = "sales.quotes";
const basePath = "/sales/quotes";
const resourcePath = "/sales/quotes/";

const empty = {
  quote_no: "",
  customer: "",
  quote_date: todayISO(),
  valid_until: todayISO(),
  payment_terms_days: "30",
  discount_amount: "0",
  tax_amount: "0",
  currency: "PKR",
  status: "draft",
  notes: "",
  lines: [emptyLine()] as Line[],
};

export default function QuoteForm({ mode }: { mode: FormMode }) {
  const params = useParams();
  const router = useRouter();
  const id = mode === "create" ? undefined : String(params.id);
  const { canChange } = usePermissions();
  const { enqueueSnackbar } = useSnackbar();
  const [busy, setBusy] = useState(false);

  const { form, setForm, loading, saving, save, readOnly } = useEntityForm({
    resourcePath,
    entityLabel: "Quotation",
    basePath,
    mode,
    id,
    empty,
    mapLoaded: (row) => ({
      quote_no: String(row.quote_no ?? ""),
      customer: row.customer != null ? String(row.customer) : "",
      quote_date: String(row.quote_date ?? empty.quote_date),
      valid_until: String(row.valid_until ?? ""),
      payment_terms_days: String(row.payment_terms_days ?? "30"),
      discount_amount: String(row.discount_amount ?? "0"),
      tax_amount: String(row.tax_amount ?? "0"),
      currency: String(row.currency ?? "PKR"),
      status: String(row.status ?? "draft"),
      notes: String(row.notes ?? ""),
      lines:
        Array.isArray(row.lines) && row.lines.length
          ? (row.lines as Record<string, unknown>[]).map((l) => ({
              item: l.item != null ? String(l.item) : "",
              description: String(l.description ?? ""),
              qty: String(l.qty ?? "1"),
              unit_price: String(l.unit_price ?? "0"),
            }))
          : [emptyLine()],
    }),
    mapPayload: (f) => ({
      quote_no: f.quote_no || undefined,
      customer: Number(f.customer),
      quote_date: f.quote_date,
      valid_until: f.valid_until || null,
      payment_terms_days: Number(f.payment_terms_days) || 30,
      discount_amount: Number(f.discount_amount) || 0,
      tax_amount: Number(f.tax_amount) || 0,
      currency: f.currency || "PKR",
      notes: f.notes || "",
      lines: (f.lines as Line[]).map((l) => ({
        item: Number(l.item),
        description: l.description || "",
        qty: Number(l.qty) || 0,
        unit_price: Number(l.unit_price) || 0,
      })),
    }),
  });

  const lines = (form.lines as Line[]) || [];
  const subtotal = useMemo(
    () => lines.reduce((a, l) => a + (Number(l.qty) || 0) * (Number(l.unit_price) || 0), 0),
    [lines]
  );
  const total = subtotal - (Number(form.discount_amount) || 0) + (Number(form.tax_amount) || 0);
  const locked = !["draft", "sent"].includes(String(form.status));
  const formReadOnly = readOnly || (mode === "edit" && locked);

  const setLine = (idx: number, patch: Partial<Line>) => {
    setForm({ ...form, lines: lines.map((l, i) => (i === idx ? { ...l, ...patch } : l)) });
  };

  const onItemChange = async (idx: number, itemId: string) => {
    setLine(idx, { item: itemId });
    if (!itemId || formReadOnly) return;
    try {
      const { data } = await api.get<Record<string, unknown>>(`/inventory/items/${itemId}/`);
      setLine(idx, {
        item: itemId,
        unit_price: String(data.sales_price ?? "0"),
        description: lines[idx].description || String(data.name ?? ""),
      });
    } catch { /* ignore */ }
  };

  const runAction = async (action: string) => {
    if (!id) return;
    setBusy(true);
    try {
      if (action === "convert") {
        const { data } = await api.post<{ sales_order_id: number; order_no: string }>(
          `${resourcePath}${id}/convert/`
        );
        enqueueSnackbar(`Converted to ${data.order_no}`, { variant: "success" });
        router.push(`/sales/orders/${data.sales_order_id}`);
        return;
      }
      const { data } = await api.post(`${resourcePath}${id}/${action}/`);
      enqueueSnackbar(`${action} ok`, { variant: "success" });
      setForm({ ...form, status: String(data.status ?? form.status) });
    } catch (e: unknown) {
      enqueueSnackbar(getApiErrorMessage(e, "Action failed"), errorSnackbarOpts);
    } finally {
      setBusy(false);
    }
  };

  return (
    <ModuleGate module={moduleKey}>
      <FormPageShell
        title={mode === "create" ? "New quotation" : mode === "edit" ? "Edit quotation" : "Quotation"}
        subtitle="Customer price offer"
        backHref={basePath}
        mode={formReadOnly && mode === "edit" ? "view" : mode}
        loading={loading}
        saving={saving}
        onSubmit={save}
        maxWidth={960}
        extraActions={
          <>
            {mode === "view" && id && canChange(moduleKey) ? (
              <Stack direction="row" spacing={1}>
                {form.status === "draft" ? (
                  <Button size="small" variant="outlined" disabled={busy} onClick={() => runAction("send")}>
                    Mark sent
                  </Button>
                ) : null}
                {["draft", "sent"].includes(String(form.status)) ? (
                  <Button size="small" variant="outlined" disabled={busy} onClick={() => runAction("accept")}>
                    Accept
                  </Button>
                ) : null}
                {["draft", "sent", "accepted"].includes(String(form.status)) ? (
                  <Button size="small" variant="contained" disabled={busy} onClick={() => runAction("convert")}>
                    Convert to SO
                  </Button>
                ) : null}
                {["draft", "sent"].includes(String(form.status)) ? (
                  <Button component={Link} href={`${basePath}/${id}/edit`} variant="contained" startIcon={<EditIcon />}>
                    Edit
                  </Button>
                ) : null}
              </Stack>
            ) : null}
          </>
        }
      >
        <Stack spacing={2}>
          <Chip size="small" label={String(form.status)} variant="outlined" sx={{ alignSelf: "flex-start" }} />
          <DetailSection title="Header" defaultExpanded>
            <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" } }}>
              <TextField label="Quote no" fullWidth value={form.quote_no} disabled={formReadOnly} helperText="Blank = auto" onChange={(e) => setForm({ ...form, quote_no: e.target.value })} />
              <RelationSelect label="Customer" required value={String(form.customer)} disabled={formReadOnly} relation={RELATIONS.customer} onChange={(v) => setForm({ ...form, customer: v })} />
              <DateTextField label="Quote date" required value={form.quote_date} disabled={formReadOnly} onChange={(e) => setForm({ ...form, quote_date: e.target.value })} />
              <DateTextField label="Valid until" value={form.valid_until} disabled={formReadOnly} notBefore={form.quote_date} onChange={(e) => setForm({ ...form, valid_until: e.target.value })} />
              <TextField label="Payment terms (days)" type="number" fullWidth value={form.payment_terms_days} disabled={formReadOnly} onChange={(e) => setForm({ ...form, payment_terms_days: e.target.value })} />
              <RelationSelect label="Currency" required value={form.currency} disabled={formReadOnly} relation={RELATIONS.currency} onChange={(v) => setForm({ ...form, currency: v })} />
              <TextField label="Notes" multiline minRows={2} fullWidth value={form.notes} disabled={formReadOnly} onChange={(e) => setForm({ ...form, notes: e.target.value })} sx={{ gridColumn: { md: "1 / -1" } }} />
            </Box>
          </DetailSection>
          <DetailSection
            title="Lines"
            description={`Total ${formatMoney(total)} ${form.currency || ""}`}
            defaultExpanded
            action={!formReadOnly ? (
              <Button size="small" startIcon={<AddIcon />} onClick={() => setForm({ ...form, lines: [...lines, emptyLine()] })}>Add line</Button>
            ) : null}
          >
            <Stack spacing={1.5}>
              {lines.map((line, idx) => (
                <Box key={idx} sx={{ display: "grid", gap: 1.5, gridTemplateColumns: { xs: "1fr", md: "2fr 1fr 1fr auto" }, p: 1.5, border: "1px solid", borderColor: "divider", borderRadius: 1 }}>
                  <RelationSelect label="Item" required value={line.item} disabled={formReadOnly} relation={RELATIONS.item} onChange={(v) => onItemChange(idx, v)} />
                  <TextField label="Qty" type="number" value={line.qty} disabled={formReadOnly} onChange={(e) => setLine(idx, { qty: e.target.value })} />
                  <TextField label="Unit price" type="number" value={line.unit_price} disabled={formReadOnly} onChange={(e) => setLine(idx, { unit_price: e.target.value })} />
                  {!formReadOnly ? (
                    <IconButton disabled={lines.length <= 1} onClick={() => setForm({ ...form, lines: lines.filter((_, i) => i !== idx) })}>
                      <DeleteOutlineIcon />
                    </IconButton>
                  ) : <span />}
                  <TextField label="Description" value={line.description} disabled={formReadOnly} onChange={(e) => setLine(idx, { description: e.target.value })} sx={{ gridColumn: { md: "1 / -1" } }} />
                </Box>
              ))}
              <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr 1fr" }, maxWidth: 560 }}>
                <TextField label="Discount" type="number" value={form.discount_amount} disabled={formReadOnly} onChange={(e) => setForm({ ...form, discount_amount: e.target.value })} />
                <TextField label="Tax" type="number" value={form.tax_amount} disabled={formReadOnly} onChange={(e) => setForm({ ...form, tax_amount: e.target.value })} />
                <Box>
                  <Typography variant="caption" color="text.secondary">Grand total</Typography>
                  <Typography variant="h6" fontWeight={700}>{formatMoney(total)} {form.currency || ""}</Typography>
                </Box>
              </Box>
            </Stack>
          </DetailSection>
        </Stack>
      </FormPageShell>
    </ModuleGate>
  );
}
