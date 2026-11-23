"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Alert,
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
import LocalShippingIcon from "@mui/icons-material/LocalShipping";
import RequestQuoteIcon from "@mui/icons-material/RequestQuote";
import { useParams } from "next/navigation";
import { useSnackbar } from "notistack";
import FormPageShell from "@/components/crud/FormPageShell";
import { DetailSection } from "@/components/crud/DetailPageShell";
import RelationSelect, { RELATIONS } from "@/components/crud/RelationSelect";
import ModuleGate from "@/components/ModuleGate";
import WorkflowActions from "@/components/WorkflowActions";
import { useEntityForm, type FormMode } from "@/hooks/useEntityForm";
import { usePermissions } from "@/hooks/usePermissions";
import api from "@/lib/api";
import { errorSnackbarOpts, getApiErrorMessage } from "@/lib/apiError";
import { formatMoney } from "@/lib/format";

type Line = {
  id?: number;
  item: string;
  description: string;
  qty: string;
  unit_price: string;
  warehouse: string;
  qty_received?: string;
  qty_this_receipt?: string;
  item_track_batch?: boolean;
  item_track_serial?: boolean;
  batch_no?: string;
  expiry_date?: string;
  serial_nos?: string;
};

const emptyLine = (): Line => ({
  item: "",
  description: "",
  qty: "1",
  unit_price: "0",
  warehouse: "",
});

const moduleKey = "procurement.orders";
const basePath = "/procurement/orders";
const resourcePath = "/procurement/orders/";

const empty = {
  po_no: "",
  vendor: "",
  warehouse: "",
  order_date: todayISO(),
  expected_date: todayISO(),
  vendor_ref: "",
  payment_terms_days: "30",
  discount_amount: "0",
  tax_amount: "0",
  currency: "PKR",
  status: "draft",
  notes: "",
  lines: [emptyLine()] as Line[],
  fulfillment: null as null | { pct?: number; open?: string },
};

export default function PurchaseOrderForm({ mode }: { mode: FormMode }) {
  const params = useParams();
  const router = useRouter();
  const id = mode === "create" ? undefined : String(params.id);
  const { canChange } = usePermissions();
  const { enqueueSnackbar } = useSnackbar();
  const [busy, setBusy] = useState(false);
  const [match, setMatch] = useState<null | {
    ok?: boolean;
    status?: string;
    detail?: string;
    po_value?: string;
    received_value?: string;
    invoice_amount?: string | null;
    grn_count?: number;
  }>(null);

  const { form, setForm, loading, saving, save, readOnly } = useEntityForm({
    resourcePath,
    entityLabel: "Purchase order",
    basePath,
    mode,
    id,
    empty,
    mapLoaded: (row) => ({
      po_no: String(row.po_no ?? ""),
      vendor: row.vendor != null ? String(row.vendor) : "",
      warehouse: row.warehouse != null ? String(row.warehouse) : "",
      order_date: String(row.order_date ?? empty.order_date),
      expected_date: String(row.expected_date ?? ""),
      vendor_ref: String(row.vendor_ref ?? ""),
      payment_terms_days: String(row.payment_terms_days ?? "30"),
      discount_amount: String(row.discount_amount ?? "0"),
      tax_amount: String(row.tax_amount ?? "0"),
      currency: String(row.currency ?? "PKR"),
      status: String(row.status ?? "draft"),
      notes: String(row.notes ?? ""),
      fulfillment: (row.fulfillment as typeof empty.fulfillment) || null,
      lines:
        Array.isArray(row.lines) && row.lines.length
          ? (row.lines as Record<string, unknown>[]).map((l) => ({
              id: typeof l.id === "number" ? l.id : undefined,
              item: l.item != null ? String(l.item) : "",
              description: String(l.description ?? ""),
              qty: String(l.qty ?? "1"),
              unit_price: String(l.unit_price ?? "0"),
              warehouse: l.warehouse != null ? String(l.warehouse) : "",
              qty_received: String(l.qty_received ?? "0"),
              item_track_batch: Boolean(l.item_track_batch),
              item_track_serial: Boolean(l.item_track_serial),
              qty_this_receipt: String(
                Math.max(
                  0,
                  (Number(l.qty) || 0) - (Number(l.qty_received) || 0)
                )
              ),
            }))
          : [emptyLine()],
    }),
    mapPayload: (f) => ({
      po_no: f.po_no || undefined,
      vendor: Number(f.vendor),
      warehouse: f.warehouse ? Number(f.warehouse) : null,
      order_date: f.order_date,
      expected_date: f.expected_date || null,
      vendor_ref: f.vendor_ref || "",
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
        warehouse: l.warehouse ? Number(l.warehouse) : null,
      })),
    }),
  });

  const lines = (form.lines as Line[]) || [];
  const subtotal = useMemo(
    () =>
      lines.reduce(
        (a, l) => a + (Number(l.qty) || 0) * (Number(l.unit_price) || 0),
        0
      ),
    [lines]
  );
  const total =
    subtotal -
    (Number(form.discount_amount) || 0) +
    (Number(form.tax_amount) || 0);

  const setLine = (idx: number, patch: Partial<Line>) => {
    const next = lines.map((l, i) => (i === idx ? { ...l, ...patch } : l));
    setForm({ ...form, lines: next });
  };

  const onItemChange = async (idx: number, itemId: string) => {
    setLine(idx, { item: itemId });
    if (!itemId || readOnly) return;
    try {
      const { data } = await api.get<Record<string, unknown>>(
        `/inventory/items/${itemId}/`
      );
      setLine(idx, {
        item: itemId,
        unit_price: String(data.unit_cost ?? data.sales_price ?? "0"),
        description:
          lines[idx].description ||
          String(data.name ?? ""),
        warehouse:
          lines[idx].warehouse ||
          (data.default_warehouse != null ? String(data.default_warehouse) : ""),
      });
    } catch {
      /* ignore lookup errors */
    }
  };

  const locked = !["draft", "cancelled"].includes(String(form.status));
  const formReadOnly = readOnly || (mode === "edit" && locked);

  useEffect(() => {
    if (!id || mode !== "view") return;
    let cancelled = false;
    (async () => {
      try {
        const { data } = await api.get(`${resourcePath}${id}/three-way-match/`);
        if (!cancelled) setMatch(data);
      } catch {
        if (!cancelled) setMatch(null);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [id, mode]);

  const receiveGoods = async () => {
    if (!id) return;
    setBusy(true);
    try {
      const partial = lines
        .filter((l) => l.id && Number(l.qty_this_receipt) > 0)
        .map((l) => ({
          id: l.id,
          qty: Number(l.qty_this_receipt),
          batch_no: l.batch_no || undefined,
          expiry_date: l.expiry_date || undefined,
          serial_nos: l.serial_nos || undefined,
        }));
      const { data } = await api.post(`${resourcePath}${id}/receive/`, {
        warehouse: form.warehouse ? Number(form.warehouse) : undefined,
        lines: partial.length ? partial : undefined,
      });
      if (data.three_way_match) setMatch(data.three_way_match);
      const grnId = data.grn_id;
      enqueueSnackbar(
        data.grn_no
          ? data.putaway_pending
            ? `GRN ${data.grn_no} posted — put the quantity away into a bin`
            : `GRN ${data.grn_no} posted`
          : "Goods received into stock",
        { variant: "success" }
      );
      if (typeof grnId === "number") {
        router.push(`/procurement/receipts/${grnId}`);
        return;
      }
      setForm({
        ...form,
        status: String(data.status ?? form.status),
        fulfillment: data.fulfillment || form.fulfillment,
        lines: Array.isArray(data.lines)
          ? data.lines.map((l: Record<string, unknown>) => ({
              id: typeof l.id === "number" ? l.id : undefined,
              item: l.item != null ? String(l.item) : "",
              description: String(l.description ?? ""),
              qty: String(l.qty ?? "1"),
              unit_price: String(l.unit_price ?? "0"),
              warehouse: l.warehouse != null ? String(l.warehouse) : "",
              qty_received: String(l.qty_received ?? "0"),
              item_track_batch: Boolean(l.item_track_batch),
              item_track_serial: Boolean(l.item_track_serial),
              qty_this_receipt: String(
                Math.max(
                  0,
                  (Number(l.qty) || 0) - (Number(l.qty_received) || 0)
                )
              ),
            }))
          : lines,
      });
    } catch (e: unknown) {
      enqueueSnackbar(getApiErrorMessage(e, "Receive failed"), errorSnackbarOpts);
    } finally {
      setBusy(false);
    }
  };

  const createApInvoice = async () => {
    if (!id) return;
    setBusy(true);
    try {
      const { data } = await api.post<{
        id: number;
        invoice_no: string;
        href?: string;
      }>(`${resourcePath}${id}/create-invoice/`);
      enqueueSnackbar(`AP invoice ${data.invoice_no} created`, {
        variant: "success",
      });
      router.push(`/finance/invoices/${data.id}`);
    } catch (e: unknown) {
      const err = e as { response?: { data?: { invoice_id?: number } } };
      const existingId = err.response?.data?.invoice_id;
      if (existingId) {
        enqueueSnackbar("Opening existing AP invoice for this PO", {
          variant: "info",
        });
        router.push(`/finance/invoices/${existingId}`);
      } else {
        enqueueSnackbar(
          getApiErrorMessage(e, "Could not create AP invoice"),
          errorSnackbarOpts
        );
      }
    } finally {
      setBusy(false);
    }
  };

  const reload = async () => {
    if (!id) return;
    try {
      const { data } = await api.get<Record<string, unknown>>(
        `${resourcePath}${id}/`
      );
      setForm({
        ...form,
        status: String(data.status ?? form.status),
        fulfillment: (data.fulfillment as typeof form.fulfillment) || null,
      });
    } catch {
      /* ignore */
    }
  };

  const title =
    mode === "create" ? "New purchase order" : mode === "edit" ? "Edit PO" : "Purchase order";

  return (
    <ModuleGate module={moduleKey}>
      <FormPageShell
        title={title}
        subtitle="Vendor PO with LoA, GRN and AP invoice link"
        backHref={basePath}
        mode={formReadOnly && mode === "edit" ? "view" : mode}
        loading={loading}
        saving={saving}
        onSubmit={save}
        maxWidth={960}
        extraActions={
          <>
            {id && mode === "view" ? (
              <WorkflowActions
                resourcePath={resourcePath}
                id={Number(id)}
                status={String(form.status)}
                moduleKey={moduleKey}
                onDone={reload}
                showCancel
                cancelStatuses={["draft", "submitted", "approved"]}
              />
            ) : null}
            {mode === "view" &&
            form.status === "approved" &&
            canChange(moduleKey) ? (
              <Button
                variant="contained"
                color="secondary"
                startIcon={<LocalShippingIcon />}
                disabled={busy}
                onClick={receiveGoods}
              >
                {busy ? "Receiving…" : "Receive goods"}
              </Button>
            ) : null}
            {mode === "view" &&
            ["approved", "received"].includes(String(form.status)) &&
            canChange(moduleKey) ? (
              <Button
                variant="outlined"
                startIcon={<RequestQuoteIcon />}
                disabled={busy}
                onClick={createApInvoice}
              >
                Create AP invoice
              </Button>
            ) : null}
            {mode === "view" &&
            canChange(moduleKey) &&
            id &&
            ["draft", "cancelled"].includes(String(form.status)) ? (
              <Button
                component={Link}
                href={`${basePath}/${id}/edit`}
                variant="contained"
                startIcon={<EditIcon />}
              >
                Edit
              </Button>
            ) : null}
          </>
        }
      >
        <Stack spacing={2}>
          {locked && mode === "edit" ? (
            <Alert severity="info">
              This PO is {form.status}. Status changes go through Submit / Approve /
              Receive — open view mode for workflow actions.
            </Alert>
          ) : null}

          {mode === "view" && match ? (
            <Alert severity={match.ok ? "success" : "warning"}>
              3-way match: {match.detail || match.status}
              {match.po_value != null
                ? ` · PO ${match.po_value} / recv ${match.received_value}`
                : ""}
              {match.invoice_amount != null ? ` / inv ${match.invoice_amount}` : ""}
              {match.grn_count != null ? ` · ${match.grn_count} GRN` : ""}
            </Alert>
          ) : null}

          <Stack direction="row" spacing={1} alignItems="center">
            <Chip
              size="small"
              label={String(form.status || "draft")}
              color={
                form.status === "received"
                  ? "success"
                  : form.status === "approved"
                    ? "warning"
                    : form.status === "submitted"
                      ? "info"
                      : form.status === "cancelled"
                        ? "error"
                        : "default"
              }
              variant="outlined"
            />
            {form.fulfillment?.pct != null ? (
              <Typography variant="caption" color="text.secondary">
                GRN {form.fulfillment.pct}% · open {form.fulfillment.open}
              </Typography>
            ) : null}
          </Stack>

          <DetailSection title="Header" defaultExpanded>
            <Box
              sx={{
                display: "grid",
                gap: 2,
                gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" },
              }}
            >
              <TextField
                label="PO no"
                fullWidth
                value={form.po_no}
                disabled={formReadOnly}
                helperText="Leave blank to auto-generate"
                onChange={(e) => setForm({ ...form, po_no: e.target.value })}
              />
              <RelationSelect
                label="Vendor"
                required
                value={String(form.vendor ?? "")}
                disabled={formReadOnly}
                relation={RELATIONS.vendor}
                onChange={(v) => setForm({ ...form, vendor: v })}
              />
              <RelationSelect
                label="Receive warehouse"
                value={String(form.warehouse ?? "")}
                disabled={formReadOnly}
                relation={RELATIONS.warehouse}
                onChange={(v) => setForm({ ...form, warehouse: v })}
              />
              <TextField
                label="Vendor quote / ref"
                fullWidth
                value={form.vendor_ref}
                disabled={formReadOnly}
                onChange={(e) => setForm({ ...form, vendor_ref: e.target.value })}
              />
              <DateTextField
                label="Order date"
                required
                value={form.order_date}
                disabled={formReadOnly}
                onChange={(e) => setForm({ ...form, order_date: e.target.value })}
              />
              <DateTextField
                label="Expected delivery"
                value={form.expected_date}
                disabled={formReadOnly}
                notBefore={form.order_date}
                onChange={(e) =>
                  setForm({ ...form, expected_date: e.target.value })
                }
              />
              <TextField
                label="Payment terms (days)"
                type="number"
                fullWidth
                value={form.payment_terms_days}
                disabled={formReadOnly}
                onChange={(e) =>
                  setForm({ ...form, payment_terms_days: e.target.value })
                }
              />
              <RelationSelect
                label="Currency"
                required
                value={form.currency}
                disabled={formReadOnly}
                relation={RELATIONS.currency}
                onChange={(v) => setForm({ ...form, currency: v })}
              />
              <TextField
                label="Notes"
                multiline
                minRows={2}
                fullWidth
                value={form.notes}
                disabled={formReadOnly}
                onChange={(e) => setForm({ ...form, notes: e.target.value })}
                sx={{ gridColumn: { md: "1 / -1" } }}
              />
            </Box>
          </DetailSection>

          <DetailSection
            title="Lines"
            description={`Subtotal ${formatMoney(subtotal)} · Total ${formatMoney(total)} ${form.currency || ""}`}
            defaultExpanded
            action={
              !formReadOnly ? (
                <Button
                  size="small"
                  startIcon={<AddIcon />}
                  onClick={() =>
                    setForm({ ...form, lines: [...lines, emptyLine()] })
                  }
                >
                  Add line
                </Button>
              ) : null
            }
          >
            <Stack spacing={1.5}>
              {lines.map((line, idx) => (
                <Box
                  key={idx}
                  sx={{
                    display: "grid",
                    gap: 1.5,
                    gridTemplateColumns: {
                      xs: "1fr",
                      md: "minmax(0,2fr) 1fr 1fr minmax(0,1.4fr) auto",
                    },
                    alignItems: "start",
                    p: 1.5,
                    border: "1px solid",
                    borderColor: "divider",
                    borderRadius: 1,
                  }}
                >
                  <RelationSelect
                    label="Item"
                    required
                    value={line.item}
                    disabled={formReadOnly}
                    relation={RELATIONS.item}
                    onChange={(v) => onItemChange(idx, v)}
                  />
                  <TextField
                    label="Qty"
                    type="number"
                    value={line.qty}
                    disabled={formReadOnly}
                    onChange={(e) => setLine(idx, { qty: e.target.value })}
                  />
                  <TextField
                    label="Unit price"
                    type="number"
                    value={line.unit_price}
                    disabled={formReadOnly}
                    onChange={(e) =>
                      setLine(idx, { unit_price: e.target.value })
                    }
                  />
                  <RelationSelect
                    label="Warehouse"
                    value={line.warehouse}
                    disabled={formReadOnly}
                    relation={RELATIONS.warehouse}
                    onChange={(v) => setLine(idx, { warehouse: v })}
                  />
                  {!formReadOnly ? (
                    <IconButton
                      aria-label="Remove line"
                      disabled={lines.length <= 1}
                      onClick={() =>
                        setForm({
                          ...form,
                          lines: lines.filter((_, i) => i !== idx),
                        })
                      }
                    >
                      <DeleteOutlineIcon />
                    </IconButton>
                  ) : (
                    <span />
                  )}
                  <TextField
                    label="Description"
                    value={line.description}
                    disabled={formReadOnly}
                    onChange={(e) =>
                      setLine(idx, { description: e.target.value })
                    }
                    sx={{ gridColumn: { md: "1 / -1" } }}
                  />
                  {mode === "view" && line.qty_received != null ? (
                    <Box sx={{ gridColumn: { md: "1 / -1" }, display: "grid", gap: 1, gridTemplateColumns: { xs: "1fr", sm: "1fr auto" }, alignItems: "center" }}>
                      <Typography variant="caption" color="text.secondary">
                        Received {line.qty_received} of {line.qty} · open{" "}
                        {Math.max(0, (Number(line.qty) || 0) - (Number(line.qty_received) || 0))}
                      </Typography>
                      {form.status === "approved" ? (
                        <TextField
                          size="small"
                          label="Receive qty"
                          type="number"
                          value={line.qty_this_receipt ?? ""}
                          onChange={(e) => setLine(idx, { qty_this_receipt: e.target.value })}
                          sx={{ maxWidth: 140 }}
                        />
                      ) : null}
                      {form.status === "approved" && line.item_track_batch ? (
                        <Box sx={{ gridColumn: { sm: "1 / -1" }, display: "flex", gap: 1, flexWrap: "wrap" }}>
                          <TextField
                            size="small"
                            required
                            label="Batch / lot no"
                            value={line.batch_no ?? ""}
                            onChange={(e) => setLine(idx, { batch_no: e.target.value })}
                          />
                          <TextField
                            size="small"
                            type="date"
                            label="Expiry"
                            InputLabelProps={{ shrink: true }}
                            value={line.expiry_date ?? ""}
                            onChange={(e) => setLine(idx, { expiry_date: e.target.value })}
                          />
                        </Box>
                      ) : null}
                      {form.status === "approved" && line.item_track_serial ? (
                        <TextField
                          size="small"
                          required
                          multiline
                          minRows={2}
                          label="Serial numbers (one per line or comma-separated)"
                          value={line.serial_nos ?? ""}
                          onChange={(e) => setLine(idx, { serial_nos: e.target.value })}
                          sx={{ gridColumn: { sm: "1 / -1" } }}
                        />
                      ) : null}
                    </Box>
                  ) : null}
                </Box>
              ))}

              <Box
                sx={{
                  display: "grid",
                  gap: 2,
                  gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr 1fr" },
                  maxWidth: 560,
                }}
              >
                <TextField
                  label="Discount"
                  type="number"
                  value={form.discount_amount}
                  disabled={formReadOnly}
                  onChange={(e) =>
                    setForm({ ...form, discount_amount: e.target.value })
                  }
                />
                <TextField
                  label="Tax"
                  type="number"
                  value={form.tax_amount}
                  disabled={formReadOnly}
                  onChange={(e) =>
                    setForm({ ...form, tax_amount: e.target.value })
                  }
                />
                <Box>
                  <Typography variant="caption" color="text.secondary">
                    Grand total
                  </Typography>
                  <Typography variant="h6" fontWeight={700}>
                    {formatMoney(total)} {form.currency || ""}
                  </Typography>
                </Box>
              </Box>
            </Stack>
          </DetailSection>
        </Stack>
      </FormPageShell>
    </ModuleGate>
  );
}
