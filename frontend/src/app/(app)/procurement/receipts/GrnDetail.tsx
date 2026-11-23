"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Button,
  Chip,
  MenuItem,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";
import FormPageShell from "@/components/crud/FormPageShell";
import { DetailSection } from "@/components/crud/DetailPageShell";
import ModuleGate from "@/components/ModuleGate";
import { useEntityForm } from "@/hooks/useEntityForm";
import { usePermissions } from "@/hooks/usePermissions";
import { useParams } from "next/navigation";
import { useSnackbar } from "notistack";
import api from "@/lib/api";
import { errorSnackbarOpts, getApiErrorMessage } from "@/lib/apiError";
import { formatMoney } from "@/lib/format";

const moduleKey = "procurement.receipts";
const basePath = "/procurement/receipts";
const resourcePath = "/procurement/receipts/";

type GrnLine = {
  id?: number;
  item_sku?: string;
  item_name?: string;
  description?: string;
  qty?: string | number;
  qty_on_hold?: string | number;
  unit_price?: string | number;
  line_total?: string;
};

type PutawayLine = {
  line_id: number;
  item_sku: string;
  item_name: string;
  qty: string;
  suggested_bin: number | null;
  suggested_bin_code: string;
};

type PutawayPlan = {
  tracking: boolean;
  lines: PutawayLine[];
  bins: { id: number; code: string; warehouse: number }[];
};

type GrnForm = {
  grn_no: string;
  status: string;
  qc_status: string;
  receipt_date: string;
  vendor_name: string;
  po_no: string;
  purchase_order: string;
  warehouse_name: string;
  notes: string;
  total: string;
  hold_qty: string;
  lines: GrnLine[];
};

export default function GrnDetail() {
  const params = useParams();
  const id = String(params.id);
  const { canChange } = usePermissions();
  const { enqueueSnackbar } = useSnackbar();
  const [busy, setBusy] = useState(false);
  const [plan, setPlan] = useState<PutawayPlan | null>(null);
  const [binChoice, setBinChoice] = useState<Record<number, string>>({});

  const { form, setForm, loading, reload } = useEntityForm<GrnForm>({
    resourcePath,
    entityLabel: "Goods receipt",
    basePath,
    mode: "view",
    id,
    empty: {
      grn_no: "",
      status: "",
      qc_status: "pending",
      receipt_date: "",
      vendor_name: "",
      po_no: "",
      purchase_order: "",
      warehouse_name: "",
      notes: "",
      total: "0",
      hold_qty: "0",
      lines: [],
    },
    mapLoaded: (row) => ({
      grn_no: String(row.grn_no ?? ""),
      status: String(row.status ?? ""),
      qc_status: String(row.qc_status ?? "pending"),
      receipt_date: String(row.receipt_date ?? ""),
      vendor_name: String(row.vendor_name ?? ""),
      po_no: String(row.po_no ?? ""),
      purchase_order: row.purchase_order != null ? String(row.purchase_order) : "",
      warehouse_name: String(row.warehouse_name ?? ""),
      notes: String(row.notes ?? ""),
      total: String(row.total ?? "0"),
      hold_qty: String(row.hold_qty ?? "0"),
      lines: Array.isArray(row.lines) ? (row.lines as GrnLine[]) : [],
    }),
  });

  useEffect(() => {
    if (!id) return;
    let cancel = false;
    (async () => {
      try {
        const { data } = await api.get<PutawayPlan>(`${resourcePath}${id}/put-away/`);
        if (cancel) return;
        setPlan(data);
        setBinChoice(
          Object.fromEntries(
            (data.lines || []).map((ln) => [
              ln.line_id,
              ln.suggested_bin ? String(ln.suggested_bin) : "",
            ])
          )
        );
      } catch {
        if (!cancel) setPlan(null);
      }
    })();
    return () => {
      cancel = true;
    };
  }, [id, form.grn_no, form.status]);

  const openLines = (plan?.lines || []).filter((ln) => Number(ln.qty) > 0);

  const putAway = async () => {
    if (!plan) return;
    setBusy(true);
    try {
      const { data } = await api.patch<PutawayPlan>(`${resourcePath}${id}/put-away/`, {
        lines: openLines.map((ln) => ({
          line_id: ln.line_id,
          bin: Number(binChoice[ln.line_id]),
          qty: ln.qty,
        })),
      });
      setPlan(data);
      enqueueSnackbar("Stock put away into bins", { variant: "success" });
    } catch (e: unknown) {
      enqueueSnackbar(getApiErrorMessage(e, "Put-away failed"), errorSnackbarOpts);
    } finally {
      setBusy(false);
    }
  };

  const setQc = async (qc_status: string) => {
    setBusy(true);
    try {
      const { data } = await api.patch(`${resourcePath}${id}/`, { qc_status });
      setForm({ ...form, qc_status: String(data.qc_status ?? qc_status) });
      enqueueSnackbar(`QC set to ${qc_status}`, { variant: "success" });
      await reload();
    } catch (e: unknown) {
      enqueueSnackbar(getApiErrorMessage(e, "QC update failed"), errorSnackbarOpts);
    } finally {
      setBusy(false);
    }
  };

  return (
    <ModuleGate module={moduleKey}>
      <FormPageShell
        title={form.grn_no || "Goods receipt"}
        subtitle="Posted goods receipt"
        backHref={basePath}
        mode="view"
        loading={loading}
        extraActions={
          form.purchase_order ? (
            <Chip
              component={Link}
              href={`/procurement/orders/${form.purchase_order}`}
              clickable
              label={`PO ${form.po_no || form.purchase_order}`}
              size="small"
              variant="outlined"
            />
          ) : null
        }
      >
        <Stack spacing={2}>
          <DetailSection title="Header">
            <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }} flexWrap="wrap">
              <Chip size="small" label={form.status || "—"} variant="outlined" />
              <Chip
                size="small"
                label={`QC ${form.qc_status || "pending"}`}
                color={
                  form.qc_status === "passed"
                    ? "success"
                    : form.qc_status === "failed"
                      ? "error"
                      : "default"
                }
                variant="outlined"
              />
              <Typography variant="body2" color="text.secondary">
                {form.receipt_date || "—"}
              </Typography>
            </Stack>
            <Typography variant="body2">
              Vendor: <strong>{form.vendor_name || "—"}</strong>
            </Typography>
            <Typography variant="body2">
              Warehouse: <strong>{form.warehouse_name || "—"}</strong>
            </Typography>
            {form.notes ? (
              <Typography variant="body2" sx={{ mt: 1 }} color="text.secondary">
                {form.notes}
              </Typography>
            ) : null}
            <Typography variant="subtitle2" sx={{ mt: 1.5 }}>
              Total {formatMoney(form.total)}
              {Number(form.hold_qty) > 0
                ? ` · ${form.hold_qty} on QC hold (not available to sell or issue)`
                : ""}
            </Typography>
            {canChange(moduleKey) ? (
              <Stack direction="row" spacing={1} sx={{ mt: 1.5 }}>
                <Button size="small" disabled={busy} onClick={() => setQc("passed")}>
                  QC pass — release
                </Button>
                <Button size="small" color="error" disabled={busy} onClick={() => setQc("failed")}>
                  QC fail — quarantine
                </Button>
                <Button size="small" variant="outlined" disabled={busy} onClick={() => setQc("pending")}>
                  Reset QC
                </Button>
              </Stack>
            ) : null}
          </DetailSection>

          {plan?.tracking && openLines.length > 0 ? (
            <DetailSection title="Put away">
              <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                Received quantity is in the warehouse and not in a bin yet.
              </Typography>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>SKU</TableCell>
                    <TableCell align="right">Qty</TableCell>
                    <TableCell>Bin</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {openLines.map((ln) => (
                    <TableRow key={ln.line_id}>
                      <TableCell>{ln.item_sku}</TableCell>
                      <TableCell align="right">{ln.qty}</TableCell>
                      <TableCell sx={{ minWidth: 180 }}>
                        <TextField
                          select
                          size="small"
                          fullWidth
                          value={binChoice[ln.line_id] ?? ""}
                          onChange={(e) =>
                            setBinChoice((prev) => ({
                              ...prev,
                              [ln.line_id]: e.target.value,
                            }))
                          }
                          disabled={!canChange(moduleKey)}
                        >
                          <MenuItem value="">Select bin</MenuItem>
                          {(plan.bins || []).map((b) => (
                            <MenuItem key={b.id} value={String(b.id)}>
                              {b.code}
                            </MenuItem>
                          ))}
                        </TextField>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              {canChange(moduleKey) ? (
                <Button
                  sx={{ mt: 1.5 }}
                  variant="contained"
                  disabled={
                    busy || openLines.some((ln) => !binChoice[ln.line_id])
                  }
                  onClick={() => void putAway()}
                >
                  Put away
                </Button>
              ) : null}
            </DetailSection>
          ) : null}

          <DetailSection title="Lines">
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>SKU</TableCell>
                  <TableCell>Item</TableCell>
                  <TableCell align="right">Qty</TableCell>
                  <TableCell align="right">Price</TableCell>
                  <TableCell align="right">Line</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {(form.lines || []).length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={5}>
                      <Typography variant="body2" color="text.secondary">
                        No lines
                      </Typography>
                    </TableCell>
                  </TableRow>
                ) : (
                  form.lines.map((ln, idx) => (
                    <TableRow key={ln.id ?? idx}>
                      <TableCell>{ln.item_sku || "—"}</TableCell>
                      <TableCell>{ln.item_name || ln.description || "—"}</TableCell>
                      <TableCell align="right">{String(ln.qty ?? "—")}</TableCell>
                      <TableCell align="right">
                        {formatMoney(String(ln.unit_price ?? "0"))}
                      </TableCell>
                      <TableCell align="right">
                        {formatMoney(String(ln.line_total ?? "0"))}
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </DetailSection>
        </Stack>
      </FormPageShell>
    </ModuleGate>
  );
}
