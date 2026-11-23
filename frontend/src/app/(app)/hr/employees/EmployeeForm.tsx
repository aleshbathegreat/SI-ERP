"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Button,
  MenuItem,
  Stack,
  TextField,
  Typography,
  Chip,
  Box,
} from "@mui/material";
import EditIcon from "@mui/icons-material/Edit";
import FormPageShell from "@/components/crud/FormPageShell";
import DetailPageShell, {
  DetailGrid,
  DetailItem,
  DetailSection,
} from "@/components/crud/DetailPageShell";
import DateTextField, { todayISO } from "@/components/DateTextField";
import RelationSelect, { RELATIONS } from "@/components/crud/RelationSelect";
import ModuleGate from "@/components/ModuleGate";
import StatusChip from "@/components/crud/StatusChip";
import { useEntityForm, type FormMode } from "@/hooks/useEntityForm";
import { usePermissions } from "@/hooks/usePermissions";
import { formatDate } from "@/lib/format";
import api from "@/lib/api";

const empty = {
  employee_code: "",
  first_name: "",
  last_name: "",
  email: "",
  phone: "",
  status: "active",
  department: "",
  designation: "",
  shift: "",
  reporting_manager: "",
  user: "",
  basic_salary: "0",
  date_of_joining: todayISO(),
  date_of_birth: "",
  gender: "",
  nationality: "",
  marital_status: "",
  national_id: "",
  ntn: "",
  eobi_number: "",
  address: "",
  emergency_contact_name: "",
  emergency_contact_phone: "",
  bank_name: "",
  bank_iban: "",
  contract_type: "permanent",
  work_location: "",
  is_tax_free: false,
  is_attendance_free: false,
};

const BASE = "/hr/employees";
const MODULE = "hr.employees";

type Dossier = {
  leave_balances?: { leave_type_name?: string; available?: string; year?: number }[];
  attendance_month?: Record<string, number>;
  documents?: { title?: string; expires_on?: string; is_expired?: boolean; days_to_expiry?: number }[];
  document_compliance?: {
    compliant?: boolean;
    missing?: number;
    expired?: number;
    blocks_payroll?: boolean;
    items?: { name?: string; status?: string; code?: string }[];
  };
  job_history?: {
    event_type?: string;
    effective_date?: string;
    to_designation?: string;
    to_salary?: string | number;
    reason?: string;
  }[];
  trainings?: { title?: string; status?: string; certificate_no?: string }[];
  performance?: { period_label?: string; rating?: string | number; status?: string }[];
  probation?: { status?: string; end_date?: string }[];
};

export default function EmployeeForm({
  mode,
  id,
}: {
  mode: FormMode;
  id?: string;
}) {
  const { canChange } = usePermissions();
  const [dossier, setDossier] = useState<Dossier | null>(null);
  const { form, setForm, loading, saving, save, readOnly } = useEntityForm({
    resourcePath: "/hr/employees/",
    entityLabel: "Employee",
    basePath: BASE,
    mode,
    id,
    empty,
    mapLoaded: (row) => ({
      employee_code: String(row.employee_code ?? ""),
      first_name: String(row.first_name ?? ""),
      last_name: String(row.last_name ?? ""),
      email: String(row.email ?? ""),
      phone: String(row.phone ?? ""),
      status: String(row.status ?? "active"),
      department: row.department ? String(row.department) : "",
      designation: row.designation ? String(row.designation) : "",
      shift: row.shift ? String(row.shift) : "",
      reporting_manager: row.reporting_manager ? String(row.reporting_manager) : "",
      user: row.user ? String(row.user) : "",
      basic_salary: String(row.basic_salary ?? "0"),
      date_of_joining: String(row.date_of_joining ?? ""),
      date_of_birth: String(row.date_of_birth ?? ""),
      gender: String(row.gender ?? ""),
      nationality: String(row.nationality ?? ""),
      marital_status: String(row.marital_status ?? ""),
      national_id: String(row.national_id ?? ""),
      ntn: String(row.ntn ?? ""),
      eobi_number: String(row.eobi_number ?? ""),
      address: String(row.address ?? ""),
      emergency_contact_name: String(row.emergency_contact_name ?? ""),
      emergency_contact_phone: String(row.emergency_contact_phone ?? ""),
      bank_name: String(row.bank_name ?? ""),
      bank_iban: String(row.bank_iban ?? ""),
      contract_type: String(row.contract_type ?? "permanent"),
      work_location: String(row.work_location ?? ""),
      is_tax_free: !!row.is_tax_free,
      is_attendance_free: !!row.is_attendance_free,
      department_name: String(row.department_name ?? ""),
      designation_title: String(row.designation_title ?? ""),
      shift_name: String(row.shift_name ?? ""),
      reporting_manager_name: String(row.reporting_manager_name ?? ""),
      user_username: String(row.user_username ?? ""),
    }),
    mapPayload: (f) => ({
      employee_code: f.employee_code,
      first_name: f.first_name,
      last_name: f.last_name,
      email: f.email,
      phone: f.phone,
      status: f.status,
      department: f.department ? Number(f.department) : null,
      designation: f.designation ? Number(f.designation) : null,
      shift: f.shift ? Number(f.shift) : null,
      reporting_manager: f.reporting_manager ? Number(f.reporting_manager) : null,
      user: f.user ? Number(f.user) : null,
      basic_salary: f.basic_salary,
      date_of_joining: f.date_of_joining || null,
      date_of_birth: f.date_of_birth || null,
      gender: f.gender || "",
      nationality: f.nationality || "",
      marital_status: f.marital_status || "",
      national_id: f.national_id || "",
      ntn: f.ntn || "",
      eobi_number: f.eobi_number || "",
      address: f.address || "",
      emergency_contact_name: f.emergency_contact_name || "",
      emergency_contact_phone: f.emergency_contact_phone || "",
      bank_name: f.bank_name || "",
      bank_iban: f.bank_iban || "",
      contract_type: f.contract_type || "permanent",
      work_location: f.work_location || "",
      is_tax_free: !!f.is_tax_free,
      is_attendance_free: !!f.is_attendance_free,
    }),
  });

  useEffect(() => {
    if (mode !== "view" || !id) return;
    api
      .get(`/hr/employees/${id}/dossier/`)
      .then((r) => setDossier(r.data))
      .catch(() => setDossier(null));
  }, [mode, id]);

  if (mode === "view") {
    const att = dossier?.attendance_month || {};
    return (
      <ModuleGate module={MODULE}>
        <DetailPageShell
          eyebrow="Employee 360"
          title={`${form.first_name || ""} ${form.last_name || ""}`.trim() || "Employee"}
          subtitle={String(form.employee_code || "")}
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
            { label: "Basic salary", value: String(form.basic_salary || "0") },
            { label: "Joined", value: formatDate(String(form.date_of_joining)) },
            { label: "Contract", value: String(form.contract_type || "—") },
            {
              label: "ESS linked",
              value: form.user || form.user_username ? "Yes" : "No",
            },
          ]}
        >
          <DetailSection title="Profile" defaultExpanded>
            <DetailGrid>
              <DetailItem label="Code" value={form.employee_code} />
              <DetailItem
                label="Status"
                value={<StatusChip status={String(form.status || "")} />}
              />
              <DetailItem label="Email" value={form.email || "—"} />
              <DetailItem label="Phone" value={form.phone || "—"} />
              <DetailItem
                label="Department"
                value={String(form.department_name || form.department || "—")}
              />
              <DetailItem
                label="Designation"
                value={String(form.designation_title || form.designation || "—")}
              />
              <DetailItem
                label="Shift"
                value={String(form.shift_name || form.shift || "—")}
              />
              <DetailItem
                label="Manager"
                value={String(form.reporting_manager_name || "—")}
              />
              <DetailItem
                label="Login user"
                value={String(form.user_username || "— not linked —")}
              />
              <DetailItem label="National ID" value={form.national_id || "—"} />
              <DetailItem label="NTN" value={form.ntn || "—"} />
              <DetailItem label="EOBI #" value={form.eobi_number || "—"} />
              <DetailItem label="Bank IBAN" value={form.bank_iban || "—"} />
            </DetailGrid>
          </DetailSection>
          <DetailSection title="This month attendance" defaultExpanded>
            <DetailGrid>
              <DetailItem label="Present / WFH" value={String(att.present ?? "—")} />
              <DetailItem label="Absent" value={String(att.absent ?? "—")} />
              <DetailItem label="On leave" value={String(att.on_leave ?? "—")} />
              <DetailItem label="Half day" value={String(att.half_day ?? "—")} />
              <DetailItem label="OT minutes" value={String(att.ot_minutes ?? "—")} />
            </DetailGrid>
          </DetailSection>
          <DetailSection title="Document compliance" defaultExpanded>
            <Stack spacing={1}>
              <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap", mb: 1 }}>
                <Chip
                  size="small"
                  color={dossier?.document_compliance?.compliant ? "success" : "warning"}
                  label={
                    dossier?.document_compliance?.compliant
                      ? "Compliant"
                      : `Missing ${dossier?.document_compliance?.missing ?? "—"} / Expired ${dossier?.document_compliance?.expired ?? "—"}`
                  }
                />
                {dossier?.document_compliance?.blocks_payroll ? (
                  <Chip size="small" color="error" label="Blocks payroll" />
                ) : null}
              </Box>
              {(dossier?.document_compliance?.items || []).map((it, i) => (
                <Box key={i} sx={{ display: "flex", gap: 1, alignItems: "center" }}>
                  <Typography variant="body2" sx={{ flex: 1 }}>
                    {it.name}
                  </Typography>
                  <Chip size="small" label={it.status || "—"} />
                </Box>
              ))}
            </Stack>
          </DetailSection>
          <DetailSection title="Job history" defaultExpanded>
            <Stack spacing={1}>
              {(dossier?.job_history || []).length === 0 ? (
                <Typography variant="body2" color="text.secondary">
                  No career events yet — edits to dept / designation / salary auto-log here.
                </Typography>
              ) : (
                (dossier?.job_history || []).slice(0, 12).map((h, i) => (
                  <Box key={i} sx={{ display: "flex", gap: 1, alignItems: "center" }}>
                    <Chip size="small" label={h.event_type || "event"} />
                    <Typography variant="body2" sx={{ flex: 1 }}>
                      {h.effective_date} · {h.to_designation || "—"} · {h.to_salary ?? ""}
                    </Typography>
                  </Box>
                ))
              )}
            </Stack>
          </DetailSection>
          <DetailSection title="Leave balances" defaultExpanded={false}>
            <Stack spacing={1}>
              {(dossier?.leave_balances || []).length === 0 ? (
                <Typography variant="body2" color="text.secondary">
                  No balances for this year — run Accrue year under Leave balances.
                </Typography>
              ) : (
                (dossier?.leave_balances || []).map((b, i) => (
                  <Box key={i} sx={{ display: "flex", gap: 1, alignItems: "center" }}>
                    <Typography variant="body2" sx={{ flex: 1 }}>
                      {b.leave_type_name}
                    </Typography>
                    <Chip size="small" label={`${b.available} available`} />
                  </Box>
                ))
              )}
            </Stack>
          </DetailSection>
          <DetailSection title="Training" defaultExpanded={false}>
            <Stack spacing={1}>
              {(dossier?.trainings || []).slice(0, 8).map((t, i) => (
                <Box key={i} sx={{ display: "flex", gap: 1, alignItems: "center" }}>
                  <Typography variant="body2" sx={{ flex: 1 }}>
                    {t.title}
                    {t.certificate_no ? ` · #${t.certificate_no}` : ""}
                  </Typography>
                  <Chip size="small" label={t.status || "—"} />
                </Box>
              ))}
            </Stack>
          </DetailSection>
          <DetailSection title="Performance" defaultExpanded={false}>
            <Stack spacing={1}>
              {(dossier?.performance || []).slice(0, 6).map((p, i) => (
                <Box key={i} sx={{ display: "flex", gap: 1, alignItems: "center" }}>
                  <Typography variant="body2" sx={{ flex: 1 }}>
                    {p.period_label} · rating {p.rating}
                  </Typography>
                  <Chip size="small" label={p.status || "—"} />
                </Box>
              ))}
            </Stack>
          </DetailSection>
          <DetailSection title="Documents / expiry" defaultExpanded={false}>
            <Stack spacing={1}>
              {(dossier?.documents || []).slice(0, 8).map((d, i) => (
                <Box key={i} sx={{ display: "flex", gap: 1, alignItems: "center" }}>
                  <Typography variant="body2" sx={{ flex: 1 }}>
                    {d.title}
                  </Typography>
                  {d.is_expired ? (
                    <Chip size="small" color="error" label="Expired" />
                  ) : d.days_to_expiry != null && d.days_to_expiry <= 30 ? (
                    <Chip
                      size="small"
                      color="warning"
                      label={`${d.days_to_expiry}d left`}
                    />
                  ) : (
                    <Typography variant="caption" color="text.secondary">
                      {d.expires_on || "—"}
                    </Typography>
                  )}
                </Box>
              ))}
            </Stack>
          </DetailSection>
        </DetailPageShell>
      </ModuleGate>
    );
  }

  return (
    <ModuleGate module={MODULE}>
      <FormPageShell
        title={mode === "create" ? "New employee" : "Edit employee"}
        subtitle="Compliance master + ESS link — used by leave, payroll, attendance"
        backHref={BASE}
        mode={mode}
        loading={loading}
        saving={saving}
        onSubmit={save}
      >
        <Stack spacing={2}>
          <DetailSection title="Identity" defaultExpanded>
            <Stack spacing={2}>
              <TextField
                label="Employee code"
                required
                fullWidth
                value={form.employee_code}
                disabled={readOnly}
                onChange={(e) => setForm({ ...form, employee_code: e.target.value })}
              />
              <TextField
                label="First name"
                required
                fullWidth
                value={form.first_name}
                disabled={readOnly}
                onChange={(e) => setForm({ ...form, first_name: e.target.value })}
              />
              <TextField
                label="Last name"
                required
                fullWidth
                value={form.last_name}
                disabled={readOnly}
                onChange={(e) => setForm({ ...form, last_name: e.target.value })}
              />
              <TextField
                label="Email"
                required
                type="email"
                fullWidth
                value={form.email}
                disabled={readOnly}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
              />
              <TextField
                label="Phone"
                fullWidth
                value={form.phone}
                disabled={readOnly}
                onChange={(e) => setForm({ ...form, phone: e.target.value })}
              />
              <DateTextField
                label="Date of birth"
                value={form.date_of_birth}
                disabled={readOnly}
                onChange={(e) => setForm({ ...form, date_of_birth: e.target.value })}
              />
              <TextField
                select
                label="Gender"
                fullWidth
                value={form.gender}
                disabled={readOnly}
                onChange={(e) => setForm({ ...form, gender: e.target.value })}
              >
                <MenuItem value="">—</MenuItem>
                <MenuItem value="male">Male</MenuItem>
                <MenuItem value="female">Female</MenuItem>
                <MenuItem value="other">Other</MenuItem>
              </TextField>
              <TextField
                label="Nationality"
                fullWidth
                value={form.nationality}
                disabled={readOnly}
                onChange={(e) => setForm({ ...form, nationality: e.target.value })}
              />
            </Stack>
          </DetailSection>
          <DetailSection title="Compliance IDs" defaultExpanded>
            <Stack spacing={2}>
              <TextField
                label="National ID (CNIC / Emirates ID / Iqama)"
                fullWidth
                value={form.national_id}
                disabled={readOnly}
                onChange={(e) => setForm({ ...form, national_id: e.target.value })}
              />
              <TextField
                label="NTN"
                fullWidth
                value={form.ntn}
                disabled={readOnly}
                onChange={(e) => setForm({ ...form, ntn: e.target.value })}
              />
              <TextField
                label="EOBI number"
                fullWidth
                value={form.eobi_number}
                disabled={readOnly}
                onChange={(e) => setForm({ ...form, eobi_number: e.target.value })}
              />
              <TextField
                label="Bank name"
                fullWidth
                value={form.bank_name}
                disabled={readOnly}
                onChange={(e) => setForm({ ...form, bank_name: e.target.value })}
              />
              <TextField
                label="Bank IBAN"
                fullWidth
                value={form.bank_iban}
                disabled={readOnly}
                onChange={(e) => setForm({ ...form, bank_iban: e.target.value })}
              />
              <TextField
                label="Address"
                fullWidth
                multiline
                minRows={2}
                value={form.address}
                disabled={readOnly}
                onChange={(e) => setForm({ ...form, address: e.target.value })}
              />
              <TextField
                label="Emergency contact name"
                fullWidth
                value={form.emergency_contact_name}
                disabled={readOnly}
                onChange={(e) =>
                  setForm({ ...form, emergency_contact_name: e.target.value })
                }
              />
              <TextField
                label="Emergency contact phone"
                fullWidth
                value={form.emergency_contact_phone}
                disabled={readOnly}
                onChange={(e) =>
                  setForm({ ...form, emergency_contact_phone: e.target.value })
                }
              />
            </Stack>
          </DetailSection>
          <DetailSection title="Organization & ESS" defaultExpanded>
            <Stack spacing={2}>
              <RelationSelect
                label="Department"
                value={form.department}
                disabled={readOnly}
                relation={RELATIONS.department}
                onChange={(v) => setForm({ ...form, department: v })}
              />
              <RelationSelect
                label="Designation"
                value={form.designation}
                disabled={readOnly}
                relation={RELATIONS.designation}
                onChange={(v) => setForm({ ...form, designation: v })}
              />
              <RelationSelect
                label="Shift"
                value={form.shift}
                disabled={readOnly}
                relation={RELATIONS.shift}
                onChange={(v) => setForm({ ...form, shift: v })}
              />
              <RelationSelect
                label="Reporting manager"
                value={form.reporting_manager}
                disabled={readOnly}
                relation={{
                  ...RELATIONS.employee,
                  allowClear: true,
                  clearLabel: "— None —",
                }}
                onChange={(v) => setForm({ ...form, reporting_manager: v })}
              />
              <RelationSelect
                label="Link login user (ESS)"
                value={form.user}
                disabled={readOnly}
                helperText="Required for Employee Self-Service portal access"
                relation={RELATIONS.user}
                onChange={(v) => setForm({ ...form, user: v })}
              />
              <TextField
                select
                label="Status"
                fullWidth
                value={form.status}
                disabled={readOnly}
                onChange={(e) => setForm({ ...form, status: e.target.value })}
              >
                {["active", "probation", "on_leave", "suspended", "separated"].map(
                  (s) => (
                    <MenuItem key={s} value={s}>
                      {s}
                    </MenuItem>
                  )
                )}
              </TextField>
              <TextField
                select
                label="Contract type"
                fullWidth
                value={form.contract_type}
                disabled={readOnly}
                onChange={(e) => setForm({ ...form, contract_type: e.target.value })}
              >
                {["permanent", "contract", "intern", "consultant"].map((s) => (
                  <MenuItem key={s} value={s}>
                    {s}
                  </MenuItem>
                ))}
              </TextField>
              <TextField
                label="Work location"
                fullWidth
                value={form.work_location}
                disabled={readOnly}
                onChange={(e) => setForm({ ...form, work_location: e.target.value })}
              />
              <TextField
                label="Basic salary"
                type="number"
                fullWidth
                value={form.basic_salary}
                disabled={readOnly}
                onChange={(e) => setForm({ ...form, basic_salary: e.target.value })}
              />
              <DateTextField
                label="Date of joining"
                value={form.date_of_joining}
                disabled={readOnly}
                onChange={(e) =>
                  setForm({ ...form, date_of_joining: e.target.value })
                }
              />
              <TextField
                select
                label="Tax-free employee"
                fullWidth
                helperText="Skip income tax on payroll runs"
                value={form.is_tax_free ? "yes" : "no"}
                disabled={readOnly}
                onChange={(e) =>
                  setForm({ ...form, is_tax_free: e.target.value === "yes" })
                }
              >
                <MenuItem value="no">No</MenuItem>
                <MenuItem value="yes">Yes</MenuItem>
              </TextField>
              <TextField
                select
                label="Attendance-free employee"
                fullWidth
                helperText="Skip attendance / unpaid-leave proration on payroll"
                value={form.is_attendance_free ? "yes" : "no"}
                disabled={readOnly}
                onChange={(e) =>
                  setForm({
                    ...form,
                    is_attendance_free: e.target.value === "yes",
                  })
                }
              >
                <MenuItem value="no">No</MenuItem>
                <MenuItem value="yes">Yes</MenuItem>
              </TextField>
            </Stack>
          </DetailSection>
        </Stack>
      </FormPageShell>
    </ModuleGate>
  );
}
