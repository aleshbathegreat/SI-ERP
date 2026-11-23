"use client";

import Link from "next/link";
import { Button, TextField } from "@mui/material";
import EditIcon from "@mui/icons-material/Edit";
import FormPageShell from "@/components/crud/FormPageShell";
import ModuleGate from "@/components/ModuleGate";
import { useEntityForm, type FormMode } from "@/hooks/useEntityForm";
import { usePermissions } from "@/hooks/usePermissions";

const empty = {
  employee: "",
  leave_type: "",
  year: String(new Date().getFullYear()),
  opening: "0",
  accrued: "0",
  used: "0",
  encashed: "0",
  carried_forward: "0",
};

const BASE = "/hr/leave-balances";
const API = "/hr/leave-balances/";
const MODULE = "hr.leaves";

export default function LeaveBalanceFormPage({
  mode,
  id,
}: {
  mode: FormMode;
  id?: string;
}) {
  const { canChange } = usePermissions();
  const { form, setForm, loading, saving, save, readOnly } = useEntityForm({
    resourcePath: API,
    entityLabel: "Leave balance",
    basePath: BASE,
    mode,
    id,
    empty,
    mapLoaded: (row) => ({
      employee: String(row.employee ?? ""),
      leave_type: String(row.leave_type ?? ""),
      year: String(row.year ?? new Date().getFullYear()),
      opening: String(row.opening ?? "0"),
      accrued: String(row.accrued ?? "0"),
      used: String(row.used ?? "0"),
      encashed: String(row.encashed ?? "0"),
      carried_forward: String(row.carried_forward ?? "0"),
    }),
    mapPayload: (f) => ({
      employee: Number(f.employee),
      leave_type: Number(f.leave_type),
      year: Number(f.year),
      opening: f.opening,
      accrued: f.accrued,
      used: f.used,
      encashed: f.encashed,
      carried_forward: f.carried_forward,
    }),
  });

  const lockKeys = mode === "edit";
  const title =
    mode === "create"
      ? "Add balance"
      : mode === "edit"
        ? "Edit balance"
        : "View balance";

  return (
    <ModuleGate module={MODULE}>
      <FormPageShell
        title={title}
        subtitle={
          mode === "view"
            ? "Read-only record"
            : mode === "create"
              ? "Fill in the fields and create the record"
              : "Update fields and save changes"
        }
        backHref={BASE}
        mode={mode}
        loading={loading}
        saving={saving}
        onSubmit={save}
        extraActions={
          mode === "view" && canChange(MODULE) && id ? (
            <Button
              component={Link}
              href={`${BASE}/${id}/edit`}
              variant="contained"
              startIcon={<EditIcon />}
            >
              Edit
            </Button>
          ) : null
        }
      >
        <TextField
          label="Employee ID"
          type="number"
          fullWidth
          value={form.employee}
          disabled={readOnly || lockKeys}
          onChange={(e) => setForm({ ...form, employee: e.target.value })}
        />
        <TextField
          label="Leave type ID"
          type="number"
          fullWidth
          value={form.leave_type}
          disabled={readOnly || lockKeys}
          onChange={(e) => setForm({ ...form, leave_type: e.target.value })}
        />
        <TextField
          label="Year"
          type="number"
          fullWidth
          value={form.year}
          disabled={readOnly}
          onChange={(e) => setForm({ ...form, year: e.target.value })}
        />
        <TextField
          label="Opening"
          type="number"
          fullWidth
          value={form.opening}
          disabled={readOnly}
          onChange={(e) => setForm({ ...form, opening: e.target.value })}
        />
        <TextField
          label="Accrued"
          type="number"
          fullWidth
          value={form.accrued}
          disabled={readOnly}
          onChange={(e) => setForm({ ...form, accrued: e.target.value })}
        />
        <TextField
          label="Used"
          type="number"
          fullWidth
          value={form.used}
          disabled={readOnly}
          onChange={(e) => setForm({ ...form, used: e.target.value })}
        />
        <TextField
          label="Encashed"
          type="number"
          fullWidth
          value={form.encashed}
          disabled={readOnly}
          onChange={(e) => setForm({ ...form, encashed: e.target.value })}
        />
        <TextField
          label="Carried forward"
          type="number"
          fullWidth
          value={form.carried_forward}
          disabled={readOnly}
          onChange={(e) => setForm({ ...form, carried_forward: e.target.value })}
        />
      </FormPageShell>
    </ModuleGate>
  );
}
