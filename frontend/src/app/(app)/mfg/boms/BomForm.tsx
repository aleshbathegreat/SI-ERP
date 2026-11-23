"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import {
  Box,
  Button,
  Chip,
  IconButton,
  MenuItem,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
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

type Line = { component: string; qty: string };

const emptyLine = (): Line => ({ component: "", qty: "1" });
const moduleKey = "mfg.bom";
const basePath = "/mfg/boms";
const resourcePath = "/mfg/boms/";

const empty = {
  code: "",
  name: "",
  item: "",
  is_active: true,
  lines: [emptyLine()] as Line[],
};

export default function BomForm({ mode }: { mode: FormMode }) {
  const params = useParams();
  const id = mode === "create" ? undefined : String(params.id);
  const { canChange } = usePermissions();
  const { enqueueSnackbar } = useSnackbar();

  const { form, setForm, loading, saving, save, readOnly } = useEntityForm({
    resourcePath,
    entityLabel: "BOM",
    basePath,
    mode,
    id,
    empty,
    mapLoaded: (row) => ({
      code: String(row.code ?? ""),
      name: String(row.name ?? ""),
      item: row.item != null ? String(row.item) : "",
      is_active: row.is_active !== false,
      lines:
        Array.isArray(row.lines) && row.lines.length
          ? (row.lines as Record<string, unknown>[]).map((l) => ({
              component: l.component != null ? String(l.component) : "",
              qty: String(l.qty ?? "1"),
            }))
          : mode === "view"
            ? []
            : [emptyLine()],
    }),
    mapPayload: (f) => ({
      code: f.code,
      name: f.name,
      item: Number(f.item),
      is_active: f.is_active !== false,
      lines: (f.lines as Line[])
        .filter((l) => l.component)
        .map((l) => ({ component: Number(l.component), qty: Number(l.qty) || 0 })),
    }),
  });

  const lines = (form.lines as Line[]) || [];
  const setLine = (idx: number, patch: Partial<Line>) =>
    setForm({ ...form, lines: lines.map((l, i) => (i === idx ? { ...l, ...patch } : l)) });

  const validateAndSave = () => {
    if (!String(form.code).trim() || !String(form.name).trim() || !form.item) {
      enqueueSnackbar("Code, name and finished good are required", { variant: "warning" });
      return;
    }
    const filled = lines.filter((l) => l.component);
    if (filled.length === 0) {
      enqueueSnackbar("Add at least one component line", { variant: "warning" });
      return;
    }
    if (filled.some((l) => !(Number(l.qty) > 0))) {
      enqueueSnackbar("Component quantities must be greater than zero", { variant: "warning" });
      return;
    }
    if (filled.some((l) => l.component === String(form.item))) {
      enqueueSnackbar("A component cannot be the finished good itself", { variant: "warning" });
      return;
    }
    void save();
  };

  return (
    <ModuleGate module={moduleKey}>
      <FormPageShell
        title={mode === "create" ? "New BOM" : mode === "edit" ? "Edit BOM" : "Bill of materials"}
        subtitle="Finished good recipe with component lines"
        backHref={basePath}
        mode={mode}
        loading={loading}
        saving={saving}
        onSubmit={validateAndSave}
        maxWidth={960}
        extraActions={
          mode === "view" && id && canChange(moduleKey) ? (
            <Button
              component={Link}
              href={`${basePath}/${id}/edit`}
              variant="contained"
              startIcon={<EditIcon />}
            >
              Edit
            </Button>
          ) : null
        }
      >
        <Stack spacing={2}>
          {mode === "view" ? (
            <Chip
              size="small"
              label={form.is_active ? "active" : "inactive"}
              variant="outlined"
              sx={{ alignSelf: "flex-start" }}
            />
          ) : null}
          <DetailSection title="Header" defaultExpanded>
            <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" } }}>
              <TextField
                label="Code"
                required
                fullWidth
                value={form.code}
                disabled={readOnly}
                onChange={(e) => setForm({ ...form, code: e.target.value })}
              />
              <TextField
                label="Name"
                required
                fullWidth
                value={form.name}
                disabled={readOnly}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
              />
              <RelationSelect
                label="Finished good"
                required
                value={String(form.item)}
                disabled={readOnly}
                relation={RELATIONS.item}
                onChange={(v) => setForm({ ...form, item: v })}
              />
              <TextField
                select
                label="Active"
                fullWidth
                value={form.is_active ? "yes" : "no"}
                disabled={readOnly}
                onChange={(e) => setForm({ ...form, is_active: e.target.value === "yes" })}
              >
                <MenuItem value="yes">Yes</MenuItem>
                <MenuItem value="no">No</MenuItem>
              </TextField>
            </Box>
          </DetailSection>
          <DetailSection
            title="Components"
            description={`${lines.length} line(s) — quantity per 1 unit of finished good`}
            defaultExpanded
            collapsible={false}
            action={
              !readOnly ? (
                <Button
                  size="small"
                  startIcon={<AddIcon />}
                  onClick={() => setForm({ ...form, lines: [...lines, emptyLine()] })}
                >
                  Add line
                </Button>
              ) : null
            }
          >
            <Stack spacing={1.5}>
              {lines.length === 0 ? (
                <Typography variant="body2" color="text.secondary">
                  No component lines — work orders on this BOM cannot be completed.
                </Typography>
              ) : null}
              {lines.map((line, idx) => (
                <Box
                  key={idx}
                  sx={{
                    display: "grid",
                    gap: 1.5,
                    gridTemplateColumns: { xs: "1fr", md: "3fr 1fr auto" },
                    p: 1.5,
                    border: "1px solid",
                    borderColor: "divider",
                    borderRadius: 1,
                    alignItems: "start",
                  }}
                >
                  <RelationSelect
                    label="Component"
                    required
                    value={line.component}
                    disabled={readOnly}
                    relation={RELATIONS.item}
                    onChange={(v) => setLine(idx, { component: v })}
                  />
                  <TextField
                    label="Qty"
                    type="number"
                    value={line.qty}
                    disabled={readOnly}
                    onChange={(e) => setLine(idx, { qty: e.target.value })}
                  />
                  {!readOnly ? (
                    <IconButton
                      aria-label="Remove line"
                      disabled={lines.length <= 1}
                      onClick={() =>
                        setForm({ ...form, lines: lines.filter((_, i) => i !== idx) })
                      }
                    >
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
