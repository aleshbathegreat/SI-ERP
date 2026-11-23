"use client";

import { useMemo, useState } from "react";
import { useParams } from "next/navigation";
import { Box, Button, Chip, Stack, TextField, Typography } from "@mui/material";
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

const moduleKey = "procurement.landed_cost";
const basePath = "/procurement/landed-costs";
const resourcePath = "/procurement/landed-costs/";

// GRN relation — reuse purchaseOrder-style label via receipts API
const GRN_REL = {
  apiPath: "/procurement/receipts/",
  listPath: "/procurement/receipts",
  entityLabel: "Goods receipt",
  getOptionLabel: (r: Record<string, unknown>) =>
    `${r.grn_no || r.id}${r.vendor_name ? ` · ${r.vendor_name}` : ""}`,
};

export default function LandedCostForm({ mode }: { mode: FormMode }) {
  const params = useParams();
  const id = mode === "create" ? undefined : String(params.id);
  const { canChange } = usePermissions();
  const { enqueueSnackbar } = useSnackbar();
  const [busy, setBusy] = useState(false);

  const empty = useMemo(
    () => ({
      goods_receipt: "",
      freight_amount: "0",
      duty_amount: "0",
      other_amount: "0",
      status: "draft",
      notes: "",
      total_charges: "0",
      grn_no: "",
    }),
    []
  );

  const { form, setForm, loading, saving, save, reload, readOnly } = useEntityForm({
    resourcePath,
    entityLabel: "Landed cost",
    basePath,
    mode,
    id,
    empty,
    mapLoaded: (row) => ({
      goods_receipt: row.goods_receipt != null ? String(row.goods_receipt) : "",
      freight_amount: String(row.freight_amount ?? "0"),
      duty_amount: String(row.duty_amount ?? "0"),
      other_amount: String(row.other_amount ?? "0"),
      status: String(row.status ?? "draft"),
      notes: String(row.notes ?? ""),
      total_charges: String(row.total_charges ?? "0"),
      grn_no: String(row.grn_no ?? ""),
    }),
    mapPayload: (f) => ({
      goods_receipt: Number(f.goods_receipt),
      freight_amount: Number(f.freight_amount) || 0,
      duty_amount: Number(f.duty_amount) || 0,
      other_amount: Number(f.other_amount) || 0,
      notes: f.notes || "",
    }),
  });

  const formReadOnly = readOnly || mode === "view" || form.status !== "draft";

  const postDoc = async () => {
    if (!id) return;
    setBusy(true);
    try {
      await api.post(`${resourcePath}${id}/post/`);
      enqueueSnackbar("Charges allocated into item unit costs", { variant: "success" });
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
        title={mode === "create" ? "New landed cost" : "Landed cost"}
        subtitle="Freight / duty allocation into GRN unit costs"
        backHref={basePath}
        mode={formReadOnly && mode !== "create" ? "view" : mode}
        loading={loading}
        saving={saving}
        onSubmit={mode === "create" || form.status === "draft" ? save : undefined}
        maxWidth={720}
        extraActions={
          mode === "view" && form.status === "draft" && canChange(moduleKey) ? (
            <Button variant="contained" disabled={busy} onClick={postDoc}>
              Post allocation
            </Button>
          ) : null
        }
      >
        <Stack spacing={2}>
          <Chip size="small" label={String(form.status)} variant="outlined" sx={{ alignSelf: "flex-start" }} />
          <DetailSection title="Charges" defaultExpanded>
            <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" } }}>
              <RelationSelect
                label="Goods receipt"
                required
                value={String(form.goods_receipt)}
                disabled={formReadOnly}
                relation={GRN_REL as typeof RELATIONS.vendor}
                onChange={(v) => setForm({ ...form, goods_receipt: v })}
              />
              <Typography variant="body2" sx={{ alignSelf: "center" }}>
                GRN {form.grn_no || "—"} · total {formatMoney(form.total_charges)}
              </Typography>
              <TextField label="Freight" type="number" fullWidth value={form.freight_amount} disabled={formReadOnly} onChange={(e) => setForm({ ...form, freight_amount: e.target.value })} />
              <TextField label="Duty" type="number" fullWidth value={form.duty_amount} disabled={formReadOnly} onChange={(e) => setForm({ ...form, duty_amount: e.target.value })} />
              <TextField label="Other" type="number" fullWidth value={form.other_amount} disabled={formReadOnly} onChange={(e) => setForm({ ...form, other_amount: e.target.value })} />
              <TextField label="Notes" multiline minRows={2} fullWidth value={form.notes} disabled={formReadOnly} onChange={(e) => setForm({ ...form, notes: e.target.value })} sx={{ gridColumn: { md: "1 / -1" } }} />
            </Box>
          </DetailSection>
        </Stack>
      </FormPageShell>
    </ModuleGate>
  );
}
