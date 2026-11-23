"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Button, MenuItem, TextField } from "@mui/material";
import EditIcon from "@mui/icons-material/Edit";
import FormPageShell from "@/components/crud/FormPageShell";
import DetailPageShell, {
  DetailGrid,
  DetailItem,
  DetailSection,
} from "@/components/crud/DetailPageShell";
import DateTextField, { daysInclusive, todayISO } from "@/components/DateTextField";
import ModuleGate from "@/components/ModuleGate";
import { useEntityForm, type FormMode } from "@/hooks/useEntityForm";
import { usePermissions } from "@/hooks/usePermissions";
import { listResource } from "@/lib/crudApi";
import RelationSelect, { RELATIONS } from "@/components/crud/RelationSelect";
import { formatDate } from "@/lib/format";
import { codeNameLabel } from "@/lib/optionLabel";

type Emp = { id: number; employee_code: string; first_name: string; last_name: string };
type LT = { id: number; name: string; code: string };

const empty = {
  employee: "",
  leave_type: "",
  start_date: todayISO(),
  end_date: todayISO(),
  days: "1",
  is_half_day: false,
  reason: "",
  status: "pending",
};

const BASE = "/hr/leaves";
const MODULE = "hr.leaves";

export default function LeaveForm({ mode, id }: { mode: FormMode; id?: string }) {
  const { canChange } = usePermissions();
  const [employees, setEmployees] = useState<Emp[]>([]);
  const [types, setTypes] = useState<LT[]>([]);
  const { form, setForm, loading, saving, save, readOnly } = useEntityForm({
    resourcePath: "/hr/leave-requests/",
    entityLabel: "Leave request",
    basePath: BASE,
    mode,
    id,
    empty,
    mapLoaded: (row) => ({
      employee: String(row.employee ?? ""),
      leave_type: String(row.leave_type ?? ""),
      start_date: String(row.start_date ?? ""),
      end_date: String(row.end_date ?? ""),
      days: String(row.days ?? "1"),
      is_half_day: !!row.is_half_day,
      reason: String(row.reason ?? ""),
      status: String(row.status ?? "pending"),
    }),
    mapPayload: (f) => {
      const payload: Record<string, unknown> = {
        employee: Number(f.employee),
        leave_type: Number(f.leave_type),
        start_date: f.start_date,
        end_date: f.is_half_day ? f.start_date : f.end_date,
        is_half_day: !!f.is_half_day,
        reason: f.reason,
      };
      // Let API compute working days; send hint only
      if (f.days) payload.days = Number(f.days) || 0;
      // Status only editable on edit of pending — approve via WorkflowActions
      if (mode === "edit" && f.status === "pending") {
        payload.status = "pending";
      }
      return payload;
    },
  });

  useEffect(() => {
    listResource<Emp>("/hr/employees/").then(setEmployees).catch(() => undefined);
    listResource<LT>("/hr/leave-types/").then(setTypes).catch(() => undefined);
  }, []);

  const onDateChange = (patch: { start_date?: string; end_date?: string }) => {
    const start_date = patch.start_date ?? String(form.start_date);
    const end_date = patch.end_date ?? String(form.end_date);
    const days = daysInclusive(start_date, end_date);
    setForm({
      ...form,
      ...patch,
      days: days > 0 ? String(days) : form.days,
    });
  };

  const empLabel = (() => {
    const e = employees.find((x) => String(x.id) === String(form.employee));
    return e
      ? codeNameLabel(e.employee_code, `${e.first_name} ${e.last_name}`.trim())
      : form.employee
        ? `Employee #${form.employee}`
        : "—";
  })();
  const typeLabel = (() => {
    const t = types.find((x) => String(x.id) === String(form.leave_type));
    return t?.name || (form.leave_type ? `#${form.leave_type}` : "—");
  })();

  if (mode === "view") {
    return (
      <ModuleGate module={MODULE}>
        <DetailPageShell
          eyebrow="Leave request"
          title={empLabel}
          subtitle={typeLabel}
          backHref={BASE}
          status={String(form.status || "")}
          loading={loading}
          extraActions={
            canChange(MODULE) && id ? (
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
          metrics={[
            { label: "Days", value: String(form.days || "—") },
            { label: "Start", value: formatDate(String(form.start_date)) },
            { label: "End", value: formatDate(String(form.end_date)) },
            { label: "Type", value: typeLabel },
          ]}
        >
          <DetailSection title="Request details" defaultExpanded>
            <DetailGrid>
              <DetailItem label="Employee" value={empLabel} />
              <DetailItem label="Leave type" value={typeLabel} />
              <DetailItem label="Start date" value={formatDate(String(form.start_date))} />
              <DetailItem label="End date" value={formatDate(String(form.end_date))} />
            </DetailGrid>
          </DetailSection>
          <DetailSection title="Reason" defaultExpanded={false}>
            <DetailItem label="Reason" value={form.reason || "—"} fullWidth />
          </DetailSection>
        </DetailPageShell>
      </ModuleGate>
    );
  }

  return (
    <ModuleGate module={MODULE}>
      <FormPageShell
        title={mode === "create" ? "New leave request" : "Edit leave request"}
        subtitle="Working days exclude weekends/holidays — approve via list Workflow actions"
        backHref={BASE}
        mode={mode}
        loading={loading}
        saving={saving}
        onSubmit={save}
        extraActions={null}
      >
        <RelationSelect
          label="Employee"
          required
          value={form.employee}
          disabled={readOnly}
          relation={RELATIONS.employee}
          onChange={(v) => setForm({ ...form, employee: v })}
        />
        <RelationSelect
          label="Leave type"
          required
          value={form.leave_type}
          disabled={readOnly}
          relation={RELATIONS.leaveType}
          onChange={(v) => setForm({ ...form, leave_type: v })}
        />
        <TextField
          select
          label="Half day"
          fullWidth
          value={form.is_half_day ? "yes" : "no"}
          disabled={readOnly}
          onChange={(e) =>
            setForm({
              ...form,
              is_half_day: e.target.value === "yes",
              days: e.target.value === "yes" ? "0.5" : form.days,
              end_date:
                e.target.value === "yes" ? form.start_date : form.end_date,
            })
          }
        >
          <MenuItem value="no">No — full day(s)</MenuItem>
          <MenuItem value="yes">Yes — 0.5 day</MenuItem>
        </TextField>
        <DateTextField
          label="Start date"
          required
          value={form.start_date}
          disabled={readOnly}
          onChange={(e) => onDateChange({ start_date: e.target.value })}
        />
        <DateTextField
          label="End date"
          required
          value={form.end_date}
          disabled={readOnly || !!form.is_half_day}
          notBefore={String(form.start_date || "")}
          onChange={(e) => onDateChange({ end_date: e.target.value })}
        />
        <TextField
          label="Days (hint)"
          type="number"
          fullWidth
          value={form.days}
          disabled={readOnly}
          helperText="Server recalculates working days on save (excludes weekends/holidays)"
          onChange={(e) => setForm({ ...form, days: e.target.value })}
        />
        <TextField
          label="Reason"
          multiline
          minRows={2}
          fullWidth
          value={form.reason}
          disabled={readOnly}
          onChange={(e) => setForm({ ...form, reason: e.target.value })}
        />
      </FormPageShell>
    </ModuleGate>
  );
}
