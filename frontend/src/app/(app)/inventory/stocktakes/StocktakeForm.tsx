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
  Typography,
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

type Line = { item: string; system_qty: string; counted_qty: string; variance?: string };
const emptyLine = (): Line => ({ item: "", system_qty: "0", counted_qty: "0" });
const moduleKey = "inventory.stocktake";
const basePath = "/inventory/stocktakes";
const resourcePath = "/inventory/stocktakes/";

export default function StocktakeForm({ mode }: { mode: FormMode }) {
  const params = useParams();
  const id = mode === "create" ? undefined : String(params.id);
  const { canChange } = usePermissions();
  const { enqueueSnackbar } = useSnackbar();
  const [busy, setBusy] = useState(false);

  const empty = useMemo(
    () => ({
      st_no: "",
      warehouse: "",
      count_date: todayISO(),
      status: "draft",
      notes: "",
      lines: [emptyLine()] as Line[],
    }),
    []
  );

  const { form, setForm, loading, saving, save, reload, readOnly } = useEntityForm({
    resourcePath,
    entityLabel: "Stocktake",
    basePath,
    mode,
    id,
    empty,
    mapLoaded: (row) => ({
      st_no: String(row.st_no ?? ""),
      warehouse: row.warehouse != null ? String(row.warehouse) : "",
      count_date: String(row.count_date ?? empty.count_date),
      status: String(row.status ?? "draft"),
      notes: String(row.notes ?? ""),
      lines:
        Array.isArray(row.lines) && row.lines.length
          ? (row.lines as Record<string, unknown>[]).map((l) => ({
              item: l.item != null ? String(l.item) : "",
              system_qty: String(l.system_qty ?? "0"),
              counted_qty: String(l.counted_qty ?? "0"),
              variance: String(l.variance ?? "0"),
            }))
          : [emptyLine()],
    }),
    mapPayload: (f) => ({
      st_no: f.st_no || undefined,
      warehouse: Number(f.warehouse),
      count_date: f.count_date,
      notes: f.notes || "",
      lines: (f.lines as Line[]).map((l) => ({
        item: Number(l.item),
        counted_qty: Number(l.counted_qty) || 0,
      })),
    }),
  });

  const lines = (form.lines as Line[]) || [];
  const formReadOnly = readOnly || (mode === "edit" && form.status !== "draft");
  const setLine = (idx: number, patch: Partial<Line>) => {
    setForm({ ...form, lines: lines.map((l, i) => (i === idx ? { ...l, ...patch } : l)) });
  };

  const postDoc = async () => {
    if (!id) return;
    setBusy(true);
    try {
      await api.post(`${resourcePath}${id}/post/`);
      enqueueSnackbar("Stocktake posted — variances adjusted", { variant: "success" });
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
        title={mode === "create" ? "New stocktake" : mode === "edit" ? "Edit stocktake" : "Stocktake"}
        subtitle="Count vs system · post variance StockMovement"
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
                Post variances
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
              <TextField label="Doc no" fullWidth value={form.st_no} disabled={formReadOnly} helperText="Blank = auto" onChange={(e) => setForm({ ...form, st_no: e.target.value })} />
              <DateTextField label="Count date" required value={form.count_date} disabled={formReadOnly} onChange={(e) => setForm({ ...form, count_date: e.target.value })} />
              <RelationSelect label="Warehouse" required value={String(form.warehouse)} disabled={formReadOnly} relation={RELATIONS.warehouse} onChange={(v) => setForm({ ...form, warehouse: v })} />
              <TextField label="Notes" multiline minRows={2} fullWidth value={form.notes} disabled={formReadOnly} onChange={(e) => setForm({ ...form, notes: e.target.value })} sx={{ gridColumn: { md: "1 / -1" } }} />
            </Box>
          </DetailSection>
          <DetailSection
            title="Lines"
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
                <Box key={idx} sx={{ display: "grid", gap: 1.5, gridTemplateColumns: { xs: "1fr", md: "2fr 1fr 1fr 1fr auto" }, p: 1.5, border: "1px solid", borderColor: "divider", borderRadius: 1 }}>
                  <RelationSelect label="Item" required value={line.item} disabled={formReadOnly} relation={RELATIONS.item} onChange={(v) => setLine(idx, { item: v })} />
                  <TextField label="System qty" value={line.system_qty} disabled helperText="Captured on save/post" />
                  <TextField label="Counted qty" type="number" value={line.counted_qty} disabled={formReadOnly} onChange={(e) => setLine(idx, { counted_qty: e.target.value })} />
                  <Typography variant="body2" sx={{ alignSelf: "center" }}>
                    Var {line.variance ?? (Number(line.counted_qty) - Number(line.system_qty) || 0)}
                  </Typography>
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
