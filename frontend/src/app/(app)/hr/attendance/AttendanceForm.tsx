"use client";

import Link from "next/link";
import { useState } from "react";
import {
  Alert,
  Button,
  MenuItem,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import EditIcon from "@mui/icons-material/Edit";
import LoginIcon from "@mui/icons-material/Login";
import LogoutIcon from "@mui/icons-material/Logout";
import FormPageShell from "@/components/crud/FormPageShell";
import DetailPageShell, {
  DetailGrid,
  DetailItem,
  DetailSection,
} from "@/components/crud/DetailPageShell";
import DateTextField, { todayISO } from "@/components/DateTextField";
import RelationSelect, { RELATIONS } from "@/components/crud/RelationSelect";
import ModuleGate from "@/components/ModuleGate";
import { useEntityForm, type FormMode } from "@/hooks/useEntityForm";
import { usePermissions } from "@/hooks/usePermissions";
import { formatDate } from "@/lib/format";
import StatusChip from "@/components/crud/StatusChip";
import api from "@/lib/api";
import { errorSnackbarOpts, getApiErrorMessage } from "@/lib/apiError";
import { useSnackbar } from "notistack";

const STATUSES = [
  "present",
  "absent",
  "late",
  "early_leave",
  "half_day",
  "wfh",
  "on_leave",
  "holiday",
  "exempt",
  "exception",
  "regularized",
];

const empty = {
  employee: "",
  work_date: todayISO(),
  check_in: "",
  check_out: "",
  status: "present",
  work_type: "office",
  is_half_day: false,
  notes: "",
  regularize_reason: "",
  late_minutes: 0,
  early_leave_minutes: 0,
  overtime_minutes: 0,
  worked_minutes: 0,
  worked_hours: 0,
  source: "manual",
  is_attendance_free: false,
};

const BASE = "/hr/attendance";
const MODULE = "hr.attendance";

export default function AttendanceForm({ mode, id }: { mode: FormMode; id?: string }) {
  const { canChange, canAdd } = usePermissions();
  const { enqueueSnackbar } = useSnackbar();
  const [punching, setPunching] = useState(false);

  const { form, setForm, loading, saving, save, readOnly } = useEntityForm({
    resourcePath: "/hr/attendance/",
    entityLabel: "Attendance",
    basePath: BASE,
    mode,
    id,
    empty,
    mapLoaded: (row) => ({
      employee: String(row.employee ?? ""),
      work_date: String(row.work_date ?? empty.work_date),
      check_in: String(row.check_in ?? "").slice(0, 8),
      check_out: String(row.check_out ?? "").slice(0, 8),
      status: String(row.status ?? "present"),
      work_type: String(row.work_type ?? "office"),
      is_half_day: !!row.is_half_day,
      notes: String(row.notes ?? ""),
      regularize_reason: String(row.regularize_reason ?? ""),
      late_minutes: Number(row.late_minutes ?? 0),
      early_leave_minutes: Number(row.early_leave_minutes ?? 0),
      overtime_minutes: Number(row.overtime_minutes ?? 0),
      worked_minutes: Number(row.worked_minutes ?? 0),
      worked_hours: Number(row.worked_hours ?? 0),
      source: String(row.source ?? "manual"),
      is_attendance_free: !!row.is_attendance_free,
    }),
    mapPayload: (f) => ({
      employee: f.employee ? Number(f.employee) : null,
      work_date: f.work_date || null,
      check_in: f.check_in || null,
      check_out: f.check_out || null,
      status: f.status,
      work_type: f.work_type,
      is_half_day: !!f.is_half_day,
      notes: f.notes,
      regularize_reason: f.regularize_reason || "",
    }),
  });

  const punch = async (kind: "check-in" | "check-out") => {
    if (!form.employee) {
      enqueueSnackbar("Select an employee first", { variant: "warning" });
      return;
    }
    setPunching(true);
    try {
      const { data } = await api.post(`/hr/attendance/${kind}/`, {
        employee: Number(form.employee),
        work_date: form.work_date || undefined,
      });
      enqueueSnackbar(
        data.punch_action === "exempt"
          ? "Employee is attendance-exempt"
          : kind === "check-in"
            ? "Checked in"
            : "Checked out",
        { variant: "success" }
      );
      setForm({
        ...form,
        check_in: String(data.check_in ?? "").slice(0, 8),
        check_out: String(data.check_out ?? "").slice(0, 8),
        status: String(data.status ?? form.status),
        late_minutes: Number(data.late_minutes ?? 0),
        early_leave_minutes: Number(data.early_leave_minutes ?? 0),
        overtime_minutes: Number(data.overtime_minutes ?? 0),
        worked_minutes: Number(data.worked_minutes ?? 0),
        worked_hours: Number(data.worked_hours ?? 0),
        is_attendance_free: !!data.is_attendance_free,
      });
    } catch (e: unknown) {
      enqueueSnackbar(getApiErrorMessage(e, "Punch failed"), errorSnackbarOpts);
    } finally {
      setPunching(false);
    }
  };

  if (mode === "view") {
    return (
      <ModuleGate module={MODULE}>
        <DetailPageShell
          eyebrow="Attendance"
          title={formatDate(String(form.work_date)) || "Attendance"}
          subtitle={form.employee ? `Employee #${form.employee}` : undefined}
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
        >
          {form.is_attendance_free ? (
            <Alert severity="info" sx={{ mb: 2 }}>
              This employee is attendance-exempt (no check-in/out required).
            </Alert>
          ) : null}
          <DetailSection title="Record" defaultExpanded>
            <DetailGrid>
              <DetailItem label="Employee" value={form.employee ? `#${form.employee}` : "—"} />
              <DetailItem label="Date" value={formatDate(String(form.work_date))} />
              <DetailItem label="Check-in" value={form.check_in || "—"} />
              <DetailItem label="Check-out" value={form.check_out || "—"} />
              <DetailItem
                label="Status"
                value={<StatusChip status={String(form.status || "")} />}
              />
              <DetailItem label="Work type" value={String(form.work_type || "office")} />
              <DetailItem label="Source" value={String(form.source || "manual")} />
              <DetailItem
                label="Worked"
                value={`${form.worked_hours || (Number(form.worked_minutes) / 60).toFixed(2)} h`}
              />
              <DetailItem label="Late (min)" value={String(form.late_minutes ?? 0)} />
              <DetailItem label="Early leave (min)" value={String(form.early_leave_minutes ?? 0)} />
              <DetailItem label="Overtime (min)" value={String(form.overtime_minutes ?? 0)} />
            </DetailGrid>
          </DetailSection>
          <DetailSection title="Notes" defaultExpanded={false}>
            <DetailItem label="Notes" value={form.notes || "—"} fullWidth />
            <DetailItem
              label="Regularize reason"
              value={form.regularize_reason || "—"}
              fullWidth
            />
          </DetailSection>
        </DetailPageShell>
      </ModuleGate>
    );
  }

  return (
    <ModuleGate module={MODULE}>
      <FormPageShell
        title={mode === "create" ? "New attendance" : "Edit attendance"}
        subtitle="Check-in / check-out, exemptions, WFH, half-day and regularization"
        backHref={BASE}
        mode={mode}
        loading={loading}
        saving={saving}
        onSubmit={save}
        extraActions={
          canAdd(MODULE) || canChange(MODULE) ? (
            <Stack direction="row" spacing={1}>
              <Button
                variant="outlined"
                startIcon={<LoginIcon />}
                disabled={punching || readOnly}
                onClick={() => punch("check-in")}
              >
                Check in
              </Button>
              <Button
                variant="outlined"
                startIcon={<LogoutIcon />}
                disabled={punching || readOnly}
                onClick={() => punch("check-out")}
              >
                Check out
              </Button>
            </Stack>
          ) : null
        }
      >
        <Stack spacing={2}>
          <RelationSelect
            label="Employee"
            required
            value={form.employee}
            disabled={readOnly}
            relation={RELATIONS.employee}
            onChange={(v) => setForm({ ...form, employee: v })}
          />
          <DateTextField
            label="Date"
            required
            value={form.work_date}
            disabled={readOnly}
            onChange={(e) => setForm({ ...form, work_date: e.target.value })}
          />
          <Stack direction={{ xs: "column", sm: "row" }} spacing={2}>
            <TextField
              label="Check-in"
              type="time"
              fullWidth
              InputLabelProps={{ shrink: true }}
              value={form.check_in}
              disabled={readOnly}
              onChange={(e) => setForm({ ...form, check_in: e.target.value })}
            />
            <TextField
              label="Check-out"
              type="time"
              fullWidth
              InputLabelProps={{ shrink: true }}
              value={form.check_out}
              disabled={readOnly}
              onChange={(e) => setForm({ ...form, check_out: e.target.value })}
            />
          </Stack>
          <Stack direction={{ xs: "column", sm: "row" }} spacing={2}>
            <TextField
              select
              label="Work type"
              fullWidth
              value={form.work_type}
              disabled={readOnly}
              onChange={(e) => setForm({ ...form, work_type: e.target.value })}
            >
              {["office", "wfh", "field", "half_day"].map((s) => (
                <MenuItem key={s} value={s}>
                  {s}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              select
              label="Status"
              fullWidth
              value={form.status}
              disabled={readOnly}
              onChange={(e) => setForm({ ...form, status: e.target.value })}
            >
              {STATUSES.map((s) => (
                <MenuItem key={s} value={s}>
                  {s}
                </MenuItem>
              ))}
            </TextField>
          </Stack>
          {(Number(form.late_minutes) > 0 ||
            Number(form.worked_minutes) > 0 ||
            Number(form.overtime_minutes) > 0) && (
            <Typography variant="body2" color="text.secondary">
              Worked {form.worked_hours || (Number(form.worked_minutes) / 60).toFixed(2)}h · Late{" "}
              {form.late_minutes}m · Early {form.early_leave_minutes}m · OT{" "}
              {form.overtime_minutes}m
            </Typography>
          )}
          <TextField
            label="Regularize reason"
            fullWidth
            value={form.regularize_reason}
            disabled={readOnly}
            helperText="Required when marking status as regularized"
            onChange={(e) =>
              setForm({ ...form, regularize_reason: e.target.value })
            }
          />
          <TextField
            label="Notes"
            fullWidth
            multiline
            minRows={2}
            value={form.notes}
            disabled={readOnly}
            onChange={(e) => setForm({ ...form, notes: e.target.value })}
          />
        </Stack>
      </FormPageShell>
    </ModuleGate>
  );
}
