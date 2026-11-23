"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  Box,
  Button,
  Chip,
  IconButton,
  Stack,
  TextField,
} from "@mui/material";
import DateTextField, { todayISO } from "@/components/DateTextField";
import AddIcon from "@mui/icons-material/Add";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutlined";
import EditIcon from "@mui/icons-material/Edit";
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

type Line = { item: string; description: string; qty: string; unit_price: string };
const emptyLine = (): Line => ({ item: "", description: "", qty: "1", unit_price: "0" });
const moduleKey = "sales.returns";
const basePath = "/sales/returns";
const resourcePath = "/sales/returns/";

export default function SalesReturnForm({ mode }: { mode: FormMode }) {
  const params = useParams();
  const id = mode === "create" ? undefined : String(params.id);
  const { canChange } = usePermissions();
  const { enqueueSnackbar } = useSnackbar();
  const [busy, setBusy] = useState(false);

  const empty = useMemo(
    () => ({
      rma_no: "",
      customer: "",
      sales_order: "",
      warehouse: "",
      return_date: todayISO(),
      status: "draft",
      notes: "",
      ar_credit_invoice: "",
      lines: [emptyLine()] as Line[],
    }),
    []
  );

  const { form, setForm, loading, saving, save, reload, readOnly } = useEntityForm({
    resourcePath,
    entityLabel: "Sales return",
    basePath,
    mode,
    id,
    empty,
    mapLoaded: (row) => ({
      rma_no: String(row.rma_no ?? ""),
      customer: row.customer != null ? String(row.customer) : "",
      sales_order: row.sales_order != null ? String(row.sales_order) : "",
      warehouse: row.warehouse != null ? String(row.warehouse) : "",
      return_date: String(row.return_date ?? empty.return_date),
      status: String(row.status ?? "draft"),
      notes: String(row.notes ?? ""),
      ar_credit_invoice: row.ar_credit_invoice != null ? String(row.ar_credit_invoice) : "",
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
      rma_no: f.rma_no || undefined,
      customer: Number(f.customer),
      sales_order: f.sales_order ? Number(f.sales_order) : null,
      warehouse: f.warehouse ? Number(f.warehouse) : null,
      return_date: f.return_date,
      notes: f.notes || "",
      ar_credit_invoice: f.ar_credit_invoice ? Number(f.ar_credit_invoice) : null,
      lines: (f.lines as Line[]).map((l) => ({
        item: Number(l.item),
        description: l.description || "",
        qty: Number(l.qty) || 0,
        unit_price: Number(l.unit_price) || 0,
      })),
    }),
  });

  const lines = (form.lines as Line[]) || [];
  const total = useMemo(
    () => lines.reduce((a, l) => a + (Number(l.qty) || 0) * (Number(l.unit_price) || 0), 0),
    [lines]
  );
  const formReadOnly = readOnly || (mode === "edit" && form.status !== "draft");

  const setLine = (idx: number, patch: Partial<Line>) => {
    setForm({ ...form, lines: lines.map((l, i) => (i === idx ? { ...l, ...patch } : l)) });
  };

  const postDoc = async () => {
    if (!id) return;
    setBusy(true);
    try {
      await api.post(`${resourcePath}${id}/post/`);
      enqueueSnackbar("Return posted — stock credited", { variant: "success" });
      await reload();
    } catch (e: unknown) {
      enqueueSnackbar(getApiErrorMessage(e, "Post failed"), errorSnackbarOpts);
    } finally {
      setBusy(false);
    }
  };

  return (
    <ModuleGate module={moduleKey}>
      <FormPageShell
        title={mode === "create" ? "New RMA" : mode === "edit" ? "Edit RMA" : "Sales return"}
        subtitle="Customer return · post to credit stock"
        backHref={basePath}
        mode={formReadOnly && mode === "edit" ? "view" : mode}
        loading={loading}
        saving={saving}
        onSubmit={save}
        maxWidth={960}
        extraActions={
          <>
            {mode === "view" && form.status === "draft" && canChange(moduleKey) ? (
              <Button variant="contained" disabled={busy} onClick={postDoc}>
                Post return
              </Button>
            ) : null}
            {mode === "view" && form.status === "draft" && canChange(moduleKey) && id ? (
              <Button component={Link} href={`${basePath}/${id}/edit`} variant="outlined" startIcon={<EditIcon />}>
                Edit
              </Button>
            ) : null}
          </>
        }
      >
        <Stack spacing={2}>
          <Chip size="small" label={String(form.status)} variant="outlined" sx={{ alignSelf: "flex-start" }} />
          <DetailSection title="Header" defaultExpanded>
            <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" } }}>
              <TextField label="RMA no" fullWidth value={form.rma_no} disabled={formReadOnly} helperText="Blank = auto" onChange={(e) => setForm({ ...form, rma_no: e.target.value })} />
              <DateTextField label="Return date" required value={form.return_date} disabled={formReadOnly} onChange={(e) => setForm({ ...form, return_date: e.target.value })} />
              <RelationSelect label="Customer" required value={String(form.customer)} disabled={formReadOnly} relation={RELATIONS.customer} onChange={(v) => setForm({ ...form, customer: v })} />
              <RelationSelect label="Sales order" value={String(form.sales_order)} disabled={formReadOnly} relation={RELATIONS.salesOrder} onChange={(v) => setForm({ ...form, sales_order: v })} />
              <RelationSelect label="Warehouse" value={String(form.warehouse)} disabled={formReadOnly} relation={RELATIONS.warehouse} onChange={(v) => setForm({ ...form, warehouse: v })} />
              <TextField label="AR credit invoice id" fullWidth value={form.ar_credit_invoice} disabled={formReadOnly} helperText="Optional link for later AR credit" onChange={(e) => setForm({ ...form, ar_credit_invoice: e.target.value })} />
              <TextField label="Notes" multiline minRows={2} fullWidth value={form.notes} disabled={formReadOnly} onChange={(e) => setForm({ ...form, notes: e.target.value })} sx={{ gridColumn: { md: "1 / -1" } }} />
            </Box>
          </DetailSection>
          <DetailSection
            title="Lines"
            description={formatMoney(total)}
            defaultExpanded
            action={
              !formReadOnly ? (
                <Button size="small" startIcon={<AddIcon />} onClick={() => setForm({ ...form, lines: [...lines, emptyLine()] })}>
                  Add line
                </Button>
              ) : null
            }
          >
            <Stack spacing={1.5}>
              {lines.map((line, idx) => (
                <Box key={idx} sx={{ display: "grid", gap: 1.5, gridTemplateColumns: { xs: "1fr", md: "2fr 1fr 1fr auto" }, p: 1.5, border: "1px solid", borderColor: "divider", borderRadius: 1 }}>
                  <RelationSelect label="Item" required value={line.item} disabled={formReadOnly} relation={RELATIONS.item} onChange={(v) => setLine(idx, { item: v })} />
                  <TextField label="Qty" type="number" value={line.qty} disabled={formReadOnly} onChange={(e) => setLine(idx, { qty: e.target.value })} />
                  <TextField label="Unit price" type="number" value={line.unit_price} disabled={formReadOnly} onChange={(e) => setLine(idx, { unit_price: e.target.value })} />
                  {!formReadOnly ? (
                    <IconButton disabled={lines.length <= 1} onClick={() => setForm({ ...form, lines: lines.filter((_, i) => i !== idx) })}>
                      <DeleteOutlineIcon />
                    </IconButton>
                  ) : (
                    <span />
                  )}
                </Box>
              ))}
            </Stack>
          </DetailSection>
        </Stack>
      </FormPageShell>
    </ModuleGate>
  );
}
