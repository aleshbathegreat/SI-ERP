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
import WorkflowActions from "@/components/WorkflowActions";
import { useEntityForm, type FormMode } from "@/hooks/useEntityForm";
import { usePermissions } from "@/hooks/usePermissions";
import api from "@/lib/api";
import { errorSnackbarOpts, getApiErrorMessage } from "@/lib/apiError";
import { formatMoney } from "@/lib/format";

type Line = { item: string; description: string; qty: string; unit_price: string };
const emptyLine = (): Line => ({ item: "", description: "", qty: "1", unit_price: "0" });
const moduleKey = "procurement.requisitions";
const basePath = "/procurement/requisitions";
const resourcePath = "/procurement/requisitions/";

export default function RequisitionForm({ mode }: { mode: FormMode }) {
  const params = useParams();
  const router = useRouter();
  const id = mode === "create" ? undefined : String(params.id);
  const { canChange } = usePermissions();
  const { enqueueSnackbar } = useSnackbar();
  const [busy, setBusy] = useState(false);

  const empty = useMemo(
    () => ({
      pr_no: "",
      request_date: todayISO(),
      required_date: todayISO(),
      department: "",
      preferred_vendor: "",
      warehouse: "",
      currency: "PKR",
      status: "draft",
      notes: "",
      lines: [emptyLine()] as Line[],
    }),
    []
  );

  const { form, setForm, loading, saving, save, reload, readOnly } = useEntityForm({
    resourcePath,
    entityLabel: "Purchase requisition",
    basePath,
    mode,
    id,
    empty,
    mapLoaded: (row) => ({
      pr_no: String(row.pr_no ?? ""),
      request_date: String(row.request_date ?? empty.request_date),
      required_date: String(row.required_date ?? ""),
      department: String(row.department ?? ""),
      preferred_vendor: row.preferred_vendor != null ? String(row.preferred_vendor) : "",
      warehouse: row.warehouse != null ? String(row.warehouse) : "",
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
      pr_no: f.pr_no || undefined,
      request_date: f.request_date,
      required_date: f.required_date || null,
      department: f.department || "",
      preferred_vendor: f.preferred_vendor ? Number(f.preferred_vendor) : null,
      warehouse: f.warehouse ? Number(f.warehouse) : null,
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
  const total = useMemo(
    () => lines.reduce((a, l) => a + (Number(l.qty) || 0) * (Number(l.unit_price) || 0), 0),
    [lines]
  );
  const locked = !["draft", "submitted"].includes(String(form.status));
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
        unit_price: String(data.unit_cost ?? "0"),
        description: lines[idx].description || String(data.name ?? ""),
      });
    } catch {
      /* ignore */
    }
  };

  const convert = async () => {
    if (!id) return;
    setBusy(true);
    try {
      const { data } = await api.post<{ purchase_order_id: number; po_no: string }>(
        `${resourcePath}${id}/convert/`
      );
      enqueueSnackbar(`Converted to ${data.po_no}`, { variant: "success" });
      router.push(`/procurement/orders/${data.purchase_order_id}`);
    } catch (e: unknown) {
      enqueueSnackbar(getApiErrorMessage(e, "Convert failed"), errorSnackbarOpts);
    } finally {
      setBusy(false);
    }
  };

  return (
    <ModuleGate module={moduleKey}>
      <FormPageShell
        title={
          mode === "create"
            ? "New purchase requisition"
            : mode === "edit"
              ? "Edit requisition"
              : "Purchase requisition"
        }
        subtitle="Internal demand · submit → approve → convert to PO"
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
              <Button variant="contained" disabled={busy} onClick={convert}>
                {busy ? "Converting…" : "Convert to PO"}
              </Button>
            ) : null}
            {mode === "view" &&
            canChange(moduleKey) &&
            id &&
            ["draft", "submitted"].includes(String(form.status)) ? (
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
          <Chip size="small" label={String(form.status)} variant="outlined" sx={{ alignSelf: "flex-start" }} />
          <DetailSection title="Header" defaultExpanded>
            <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" } }}>
              <TextField label="PR no" fullWidth value={form.pr_no} disabled={formReadOnly} helperText="Blank = auto" onChange={(e) => setForm({ ...form, pr_no: e.target.value })} />
              <TextField label="Department" fullWidth value={form.department} disabled={formReadOnly} onChange={(e) => setForm({ ...form, department: e.target.value })} />
              <DateTextField label="Request date" required value={form.request_date} disabled={formReadOnly} onChange={(e) => setForm({ ...form, request_date: e.target.value })} />
              <DateTextField label="Required by" value={form.required_date} disabled={formReadOnly} notBefore={form.request_date} onChange={(e) => setForm({ ...form, required_date: e.target.value })} />
              <RelationSelect label="Preferred vendor" value={String(form.preferred_vendor)} disabled={formReadOnly} relation={RELATIONS.vendor} onChange={(v) => setForm({ ...form, preferred_vendor: v })} />
              <RelationSelect label="Warehouse" value={String(form.warehouse)} disabled={formReadOnly} relation={RELATIONS.warehouse} onChange={(v) => setForm({ ...form, warehouse: v })} />
              <RelationSelect label="Currency" required value={form.currency} disabled={formReadOnly} relation={RELATIONS.currency} onChange={(v) => setForm({ ...form, currency: v })} />
              <TextField label="Notes" multiline minRows={2} fullWidth value={form.notes} disabled={formReadOnly} onChange={(e) => setForm({ ...form, notes: e.target.value })} sx={{ gridColumn: { md: "1 / -1" } }} />
            </Box>
          </DetailSection>
          <DetailSection
            title="Lines"
            description={`Est. ${formatMoney(total)} ${form.currency || ""}`}
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
                <Box
                  key={idx}
                  sx={{
                    display: "grid",
                    gap: 1.5,
                    gridTemplateColumns: { xs: "1fr", md: "2fr 1fr 1fr auto" },
                    p: 1.5,
                    border: "1px solid",
                    borderColor: "divider",
                    borderRadius: 1,
                  }}
                >
                  <RelationSelect label="Item" required value={line.item} disabled={formReadOnly} relation={RELATIONS.item} onChange={(v) => onItemChange(idx, v)} />
                  <TextField label="Qty" type="number" value={line.qty} disabled={formReadOnly} onChange={(e) => setLine(idx, { qty: e.target.value })} />
                  <TextField label="Est. price" type="number" value={line.unit_price} disabled={formReadOnly} onChange={(e) => setLine(idx, { unit_price: e.target.value })} />
                  {!formReadOnly ? (
                    <IconButton disabled={lines.length <= 1} onClick={() => setForm({ ...form, lines: lines.filter((_, i) => i !== idx) })}>
                      <DeleteOutlineIcon />
                    </IconButton>
                  ) : (
                    <span />
                  )}
                  <TextField label="Description" value={line.description} disabled={formReadOnly} onChange={(e) => setLine(idx, { description: e.target.value })} sx={{ gridColumn: { md: "1 / -1" } }} />
                </Box>
              ))}
              <Typography variant="h6" fontWeight={700}>
                {formatMoney(total)} {form.currency || ""}
              </Typography>
            </Stack>
          </DetailSection>
        </Stack>
      </FormPageShell>
    </ModuleGate>
  );
}
