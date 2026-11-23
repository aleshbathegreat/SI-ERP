"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
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
import OutboxIcon from "@mui/icons-material/Outbox";
import { useParams, useRouter } from "next/navigation";
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
  qty_delivered?: string;
  qty_this_delivery?: string;
  item_track_batch?: boolean;
  item_track_serial?: boolean;
  batch_no?: string;
  serial_nos?: string;
};

const emptyLine = (): Line => ({
  item: "",
  description: "",
  qty: "1",
  unit_price: "0",
  warehouse: "",
});

const moduleKey = "sales.orders";
const basePath = "/sales/orders";
const resourcePath = "/sales/orders/";

const empty = {
  order_no: "",
  customer: "",
  warehouse: "",
  order_date: todayISO(),
  expected_date: todayISO(),
  customer_po: "",
  payment_terms_days: "30",
  discount_amount: "0",
  tax_amount: "0",
  shipping_address: "",
  currency: "PKR",
  status: "draft",
  notes: "",
  lines: [emptyLine()] as Line[],
  fulfillment: null as null | { pct?: number; open?: string },
};

export default function SalesOrderForm({ mode }: { mode: FormMode }) {
  const params = useParams();
  const router = useRouter();
  const id = mode === "create" ? undefined : String(params.id);
  const { canChange } = usePermissions();
  const { enqueueSnackbar } = useSnackbar();
  const [busy, setBusy] = useState(false);

  const { form, setForm, loading, saving, save, readOnly } = useEntityForm({
    resourcePath,
    entityLabel: "Sales order",
    basePath,
    mode,
    id,
    empty,
    mapLoaded: (row) => ({
      order_no: String(row.order_no ?? ""),
      customer: row.customer != null ? String(row.customer) : "",
      warehouse: row.warehouse != null ? String(row.warehouse) : "",
      order_date: String(row.order_date ?? empty.order_date),
      expected_date: String(row.expected_date ?? ""),
      customer_po: String(row.customer_po ?? ""),
      payment_terms_days: String(row.payment_terms_days ?? "30"),
      discount_amount: String(row.discount_amount ?? "0"),
      tax_amount: String(row.tax_amount ?? "0"),
      shipping_address: String(row.shipping_address ?? ""),
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
              qty_delivered: String(l.qty_delivered ?? "0"),
              item_track_batch: Boolean(l.item_track_batch),
              item_track_serial: Boolean(l.item_track_serial),
              qty_this_delivery: String(
                Math.max(
                  0,
                  (Number(l.qty) || 0) - (Number(l.qty_delivered) || 0)
                )
              ),
            }))
          : [emptyLine()],
    }),
    mapPayload: (f) => ({
      order_no: f.order_no || undefined,
      customer: Number(f.customer),
      warehouse: f.warehouse ? Number(f.warehouse) : null,
      order_date: f.order_date,
      expected_date: f.expected_date || null,
      customer_po: f.customer_po || "",
      payment_terms_days: Number(f.payment_terms_days) || 30,
      discount_amount: Number(f.discount_amount) || 0,
      tax_amount: Number(f.tax_amount) || 0,
      shipping_address: f.shipping_address || "",
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
        unit_price: String(data.sales_price ?? "0"),
        description:
          lines[idx].description || String(data.name ?? ""),
        warehouse:
          lines[idx].warehouse ||
          (data.default_warehouse != null ? String(data.default_warehouse) : ""),
      });
    } catch {
      /* ignore */
    }
  };

  const locked = !["draft", "cancelled"].includes(String(form.status));
  const formReadOnly = readOnly || (mode === "edit" && locked);

  const deliverGoods = async () => {
    if (!id) return;
    setBusy(true);
    try {
      const partial = lines
        .filter((l) => l.id && Number(l.qty_this_delivery) > 0)
        .map((l) => ({
          id: l.id,
          qty: Number(l.qty_this_delivery),
          batch_no: l.batch_no || undefined,
          serial_nos: l.serial_nos || undefined,
        }));
      const { data } = await api.post(`${resourcePath}${id}/deliver/`, {
        warehouse: form.warehouse ? Number(form.warehouse) : undefined,
        lines: partial.length ? partial : undefined,
      });
      const dnId = data.dn_id;
      enqueueSnackbar(
        data.dn_no ? `DN ${data.dn_no} posted` : "Goods issued from stock",
        { variant: "success" }
      );
      if (typeof dnId === "number") {
        router.push(`/sales/deliveries/${dnId}`);
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
              qty_delivered: String(l.qty_delivered ?? "0"),
              item_track_batch: Boolean(l.item_track_batch),
              item_track_serial: Boolean(l.item_track_serial),
              qty_this_delivery: String(
                Math.max(
                  0,
                  (Number(l.qty) || 0) - (Number(l.qty_delivered) || 0)
                )
              ),
            }))
          : lines,
      });
    } catch (e: unknown) {
      enqueueSnackbar(getApiErrorMessage(e, "Delivery failed"), errorSnackbarOpts);
    } finally {
      setBusy(false);
    }
  };

  const createArInvoice = async () => {
    if (!id) return;
    setBusy(true);
    try {
      const { data } = await api.post<{ id: number; invoice_no: string }>(
        `${resourcePath}${id}/create-invoice/`
      );
      enqueueSnackbar(`AR invoice ${data.invoice_no} created`, { variant: "success" });
      router.push(`/sales/invoices/${data.id}`);
    } catch (e: unknown) {
      const err = e as { response?: { data?: { invoice_id?: number } } };
      if (err.response?.data?.invoice_id) {
        enqueueSnackbar("Opening existing AR invoice", { variant: "info" });
        router.push(`/sales/invoices/${err.response.data.invoice_id}`);
      } else {
        enqueueSnackbar(getApiErrorMessage(e, "Could not create AR invoice"), errorSnackbarOpts);
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
    mode === "create"
      ? "New sales order"
      : mode === "edit"
        ? "Edit sales order"
        : "Sales order";

  return (
    <ModuleGate module={moduleKey}>
      <FormPageShell
        title={title}
        subtitle="Customer order · confirm → deliver → invoice"
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
                submitLabel="Confirm"
                showCancel
                cancelStatuses={["draft", "confirmed"]}
              />
            ) : null}
            {mode === "view" &&
            form.status === "confirmed" &&
            canChange(moduleKey) ? (
              <Button
                variant="contained"
                color="secondary"
                startIcon={<OutboxIcon />}
                disabled={busy}
                onClick={deliverGoods}
              >
                {busy ? "Delivering…" : "Deliver / issue"}
              </Button>
            ) : null}
            {mode === "view" &&
            ["confirmed", "delivered", "invoiced"].includes(String(form.status)) &&
            canChange(moduleKey) ? (
              <Button variant="outlined" disabled={busy} onClick={createArInvoice}>
                Create AR invoice
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
              This order is {form.status}. Use Confirm / Deliver / Cancel from the
              view screen.
            </Alert>
          ) : null}

          <Stack direction="row" spacing={1} alignItems="center">
            <Chip
              size="small"
              label={String(form.status || "draft")}
              color={
                form.status === "invoiced"
                  ? "success"
                  : form.status === "delivered"
                    ? "warning"
                    : form.status === "confirmed"
                      ? "info"
                      : form.status === "cancelled"
                        ? "error"
                        : "default"
              }
              variant="outlined"
            />
            {form.fulfillment?.pct != null ? (
              <Typography variant="caption" color="text.secondary">
                Shipped {form.fulfillment.pct}% · open {form.fulfillment.open}
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
                label="Order no"
                fullWidth
                value={form.order_no}
                disabled={formReadOnly}
                helperText="Leave blank to auto-generate"
                onChange={(e) => setForm({ ...form, order_no: e.target.value })}
              />
              <RelationSelect
                label="Customer"
                required
                value={String(form.customer ?? "")}
                disabled={formReadOnly}
                relation={RELATIONS.customer}
                onChange={(v) => setForm({ ...form, customer: v })}
              />
              <RelationSelect
                label="Ship-from warehouse"
                value={String(form.warehouse ?? "")}
                disabled={formReadOnly}
                relation={RELATIONS.warehouse}
                onChange={(v) => setForm({ ...form, warehouse: v })}
              />
              <TextField
                label="Customer PO / ref"
                fullWidth
                value={form.customer_po}
                disabled={formReadOnly}
                onChange={(e) => setForm({ ...form, customer_po: e.target.value })}
              />
              <DateTextField
                label="Order date"
                required
                value={form.order_date}
                disabled={formReadOnly}
                onChange={(e) => setForm({ ...form, order_date: e.target.value })}
              />
              <DateTextField
                label="Promise / delivery date"
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
                label="Shipping address"
                multiline
                minRows={2}
                fullWidth
                value={form.shipping_address}
                disabled={formReadOnly}
                onChange={(e) =>
                  setForm({ ...form, shipping_address: e.target.value })
                }
                sx={{ gridColumn: { md: "1 / -1" } }}
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
                  {mode === "view" && line.qty_delivered != null ? (
                    <Box
                      sx={{
                        gridColumn: { md: "1 / -1" },
                        display: "grid",
                        gap: 1,
                        gridTemplateColumns: { xs: "1fr", sm: "1fr auto" },
                        alignItems: "center",
                      }}
                    >
                      <Typography variant="caption" color="text.secondary">
                        Delivered {line.qty_delivered} of {line.qty} · open{" "}
                        {Math.max(
                          0,
                          (Number(line.qty) || 0) - (Number(line.qty_delivered) || 0)
                        )}
                      </Typography>
                      {form.status === "approved" ? (
                        <TextField
                          size="small"
                          label="Deliver qty"
                          type="number"
                          value={line.qty_this_delivery ?? ""}
                          onChange={(e) =>
                            setLine(idx, { qty_this_delivery: e.target.value })
                          }
                          sx={{ maxWidth: 140 }}
                        />
                      ) : null}
                      {["approved", "confirmed"].includes(String(form.status)) &&
                      line.item_track_batch ? (
                        <TextField
                          size="small"
                          required
                          label="Batch / lot no to issue"
                          value={line.batch_no ?? ""}
                          onChange={(e) => setLine(idx, { batch_no: e.target.value })}
                          sx={{ gridColumn: { sm: "1 / -1" }, maxWidth: 320 }}
                        />
                      ) : null}
                      {["approved", "confirmed"].includes(String(form.status)) &&
                      line.item_track_serial ? (
                        <TextField
                          size="small"
                          required
                          multiline
                          minRows={2}
                          label="Serial numbers to issue (one per line or comma-separated)"
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
