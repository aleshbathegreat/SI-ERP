"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useSelector } from "react-redux";
import { Button, MenuItem, Stack, TextField, Typography } from "@mui/material";
import CalculateIcon from "@mui/icons-material/Calculate";
import EditIcon from "@mui/icons-material/Edit";
import FormPageShell from "@/components/crud/FormPageShell";
import DetailPageShell, {
  DetailGrid,
  DetailItem,
  DetailSection,
} from "@/components/crud/DetailPageShell";
import DateTextField, { addMonthsISO, todayISO } from "@/components/DateTextField";
import ModuleGate from "@/components/ModuleGate";
import { useEntityForm, type FormMode } from "@/hooks/useEntityForm";
import { usePermissions } from "@/hooks/usePermissions";
import { listResource } from "@/lib/crudApi";
import RelationSelect, { RELATIONS } from "@/components/crud/RelationSelect";
import api from "@/lib/api";
import { normalizeCurrency } from "@/lib/currencies";
import { suggestDocNo } from "@/lib/docNumbers";
import { formatDate, formatMoney } from "@/lib/format";
import { codeNameLabel } from "@/lib/optionLabel";
import type { RootState } from "@/store";

type Emp = { id: number; employee_code: string; first_name: string; last_name: string };

const LOAN_TYPES = [
  "personal",
  "housing",
  "vehicle",
  "salary_advance",
  "education",
  "medical",
  "other",
];

const LOAN_STATUSES = [
  "draft",
  "pending",
  "approved",
  "active",
  "closed",
  "rejected",
  "written_off",
];

const emptyBase = {
  loan_number: "",
  employee: "",
  loan_type: "personal",
  currency: "PKR",
  principal: "0",
  interest_rate: "0",
  tenure_months: "12",
  monthly_installment: "0",
  outstanding_balance: "0",
  start_date: todayISO(),
  end_date: todayISO(),
  status: "draft",
  purpose: "",
  guarantor: "",
  guarantor_name: "",
  deduct_from_payroll: true,
};

const BASE = "/payroll/loans";
const API = "/payroll/loans/";
const MODULE = "payroll.loans";

function computeEmiLocal(principal: number, annualRate: number, tenure: number): number {
  const n = Math.max(1, Math.floor(tenure) || 12);
  const p = principal || 0;
  if (p <= 0) return 0;
  if (!annualRate || annualRate <= 0) return Math.round((p / n) * 100) / 100;
  const r = annualRate / 100 / 12;
  const factor = Math.pow(1 + r, n);
  return Math.round(((p * r * factor) / (factor - 1)) * 100) / 100;
}

export default function LoanFormPage({
  mode,
  id,
}: {
  mode: FormMode;
  id?: string;
}) {
  const { canChange } = usePermissions();
  const orgCurrency = useSelector((s: RootState) => s.auth.organization?.currency);
  const [employees, setEmployees] = useState<Emp[]>([]);
  const [calcBusy, setCalcBusy] = useState(false);
  const [calcHint, setCalcHint] = useState("");

  const empty = useMemo(
    () =>
      mode === "create"
        ? {
            ...emptyBase,
            loan_number: suggestDocNo("LN"),
            currency: normalizeCurrency(orgCurrency),
            start_date: todayISO(),
            end_date: addMonthsISO(todayISO(), 12),
          }
        : emptyBase,
    [mode, orgCurrency]
  );

  const { form, setForm, loading, saving, save, readOnly } = useEntityForm({
    resourcePath: API,
    entityLabel: "Employee loan",
    basePath: BASE,
    mode,
    id,
    empty,
    mapLoaded: (row) => ({
      loan_number: String(row.loan_number || ""),
      employee: String(row.employee || ""),
      loan_type: String(row.loan_type || "personal"),
      currency: normalizeCurrency(String(row.currency || orgCurrency || "PKR")),
      principal: String(row.principal ?? "0"),
      interest_rate: String(row.interest_rate ?? "0"),
      tenure_months: String(row.tenure_months ?? 12),
      monthly_installment: String(row.monthly_installment ?? "0"),
      outstanding_balance: String(row.outstanding_balance ?? "0"),
      start_date: String(row.start_date || ""),
      end_date: String(row.end_date || ""),
      status: String(row.status || "draft"),
      purpose: String(row.purpose || ""),
      guarantor: row.guarantor ? String(row.guarantor) : "",
      guarantor_name: String(row.guarantor_name || ""),
      deduct_from_payroll: !!row.deduct_from_payroll,
    }),
    mapPayload: (f) => ({
      loan_number: f.loan_number,
      employee: Number(f.employee),
      loan_type: f.loan_type,
      currency: normalizeCurrency(f.currency),
      principal: f.principal,
      interest_rate: f.interest_rate,
      tenure_months: Number(f.tenure_months),
      monthly_installment: f.monthly_installment,
      outstanding_balance: f.outstanding_balance || f.principal,
      start_date: f.start_date || null,
      end_date: f.end_date || null,
      status: f.status,
      purpose: f.purpose,
      guarantor: f.guarantor ? Number(f.guarantor) : null,
      guarantor_name: f.guarantor_name || "",
      deduct_from_payroll: f.deduct_from_payroll,
    }),
  });

  useEffect(() => {
    listResource<Emp>("/hr/employees/").then(setEmployees).catch(() => undefined);
  }, []);

  const recalculateEmi = useCallback(
    async (next?: Partial<typeof emptyBase>) => {
      const merged = { ...form, ...next };
      const principal = Number(merged.principal) || 0;
      const rate = Number(merged.interest_rate) || 0;
      const tenure = Number(merged.tenure_months) || 12;
      if (principal <= 0) return;

      setCalcBusy(true);
      try {
        const { data } = await api.post<{
          monthly_installment: string;
          total_payable: string;
          total_interest: string;
        }>("/payroll/loans/calculate-emi/", {
          principal,
          interest_rate: rate,
          tenure_months: tenure,
        });
        const emi = String(data.monthly_installment);
        setForm({
          ...merged,
          monthly_installment: emi,
          outstanding_balance:
            mode === "create" || Number(merged.outstanding_balance) <= 0
              ? String(merged.principal)
              : merged.outstanding_balance,
        });
        setCalcHint(
          `EMI ${formatMoney(data.monthly_installment, merged.currency)} · total payable ${formatMoney(data.total_payable, merged.currency)} · interest ${formatMoney(data.total_interest, merged.currency)}`
        );
      } catch {
        const emi = computeEmiLocal(principal, rate, tenure);
        setForm({
          ...merged,
          monthly_installment: String(emi),
          outstanding_balance:
            mode === "create" || Number(merged.outstanding_balance) <= 0
              ? String(merged.principal)
              : merged.outstanding_balance,
        });
        setCalcHint(`EMI ${formatMoney(emi, merged.currency)} (local estimate)`);
      } finally {
        setCalcBusy(false);
      }
    },
    [form, mode, setForm]
  );

  // Auto-recalculate EMI when principal / rate / tenure change (debounced, no loop)
  useEffect(() => {
    if (readOnly) return;
    const principal = Number(form.principal) || 0;
    const rate = Number(form.interest_rate) || 0;
    const tenure = Number(form.tenure_months) || 12;
    if (principal <= 0) return;
    const currency = String(form.currency || "PKR");
    const t = setTimeout(async () => {
      setCalcBusy(true);
      try {
        const { data } = await api.post<{
          monthly_installment: string;
          total_payable: string;
          total_interest: string;
        }>("/payroll/loans/calculate-emi/", {
          principal,
          interest_rate: rate,
          tenure_months: tenure,
        });
        setForm((prev) => ({
          ...prev,
          monthly_installment: String(data.monthly_installment),
          outstanding_balance:
            mode === "create" || Number(prev.outstanding_balance) <= 0
              ? String(prev.principal)
              : prev.outstanding_balance,
        }));
        setCalcHint(
          `EMI ${formatMoney(data.monthly_installment, currency)} · total payable ${formatMoney(data.total_payable, currency)} · interest ${formatMoney(data.total_interest, currency)}`
        );
      } catch {
        const emi = computeEmiLocal(principal, rate, tenure);
        setForm((prev) => ({
          ...prev,
          monthly_installment: String(emi),
          outstanding_balance:
            mode === "create" || Number(prev.outstanding_balance) <= 0
              ? String(prev.principal)
              : prev.outstanding_balance,
        }));
        setCalcHint(`EMI ${formatMoney(emi, currency)} (local estimate)`);
      } finally {
        setCalcBusy(false);
      }
    }, 400);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [form.principal, form.interest_rate, form.tenure_months, readOnly, mode]);

  // Auto end date from start + tenure
  useEffect(() => {
    if (readOnly) return;
    const start = String(form.start_date || "");
    const tenure = Number(form.tenure_months) || 0;
    if (!start || tenure <= 0) return;
    const end = addMonthsISO(start, tenure);
    if (!end || end === form.end_date) return;
    setForm((prev) =>
      prev.end_date === end ? prev : { ...prev, end_date: end }
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [form.start_date, form.tenure_months, readOnly]);

  const title =
    mode === "create" ? "New loan" : mode === "edit" ? "Edit loan" : "View loan";

  const guarantorChoices = employees.filter(
    (e) => String(e.id) !== String(form.employee)
  );

  const employeeLabel = useMemo(() => {
    const e = employees.find((x) => String(x.id) === String(form.employee));
    if (e) return codeNameLabel(e.employee_code, `${e.first_name} ${e.last_name}`.trim());
    return form.employee ? `Employee #${form.employee}` : "—";
  }, [employees, form.employee]);

  const guarantorLabel = useMemo(() => {
    const e = employees.find((x) => String(x.id) === String(form.guarantor));
    if (e) return codeNameLabel(e.employee_code, `${e.first_name} ${e.last_name}`.trim());
    return form.guarantor_name || "—";
  }, [employees, form.guarantor, form.guarantor_name]);

  const ccy = String(form.currency || "PKR");
  const editBtn =
    mode === "view" && canChange(MODULE) && id ? (
      <Button
        component={Link}
        href={`${BASE}/${id}/edit`}
        variant="contained"
        startIcon={<EditIcon />}
      >
        Edit
      </Button>
    ) : null;

  if (mode === "view") {
    return (
      <ModuleGate module={MODULE}>
        <DetailPageShell
          eyebrow="Employee loan"
          title={String(form.loan_number || "Loan")}
          subtitle={`${String(form.loan_type || "").replace(/_/g, " ")} · ${employeeLabel}`}
          backHref={BASE}
          status={String(form.status || "")}
          loading={loading}
          extraActions={editBtn}
          metrics={[
            {
              label: "Principal",
              value: formatMoney(form.principal, ccy),
            },
            {
              label: "Monthly EMI",
              value: formatMoney(form.monthly_installment, ccy),
              hint: calcHint || undefined,
            },
            {
              label: "Outstanding",
              value: formatMoney(form.outstanding_balance, ccy),
            },
            {
              label: "Tenure",
              value: `${form.tenure_months || "—"} mo`,
              hint: `${Number(form.interest_rate || 0)}% annual`,
            },
          ]}
        >
          <DetailSection
            title="Overview"
            description="Borrower and classification"
            defaultExpanded
          >
            <DetailGrid>
              <DetailItem label="Loan number" value={form.loan_number} />
              <DetailItem label="Employee" value={employeeLabel} />
              <DetailItem
                label="Loan type"
                value={String(form.loan_type || "").replace(/_/g, " ")}
              />
              <DetailItem label="Currency" value={ccy} />
              <DetailItem
                label="Payroll deduction"
                value={form.deduct_from_payroll ? "Yes" : "No"}
              />
            </DetailGrid>
          </DetailSection>

          <DetailSection
            title="Schedule"
            description="Disbursement window"
            defaultExpanded={false}
          >
            <DetailGrid>
              <DetailItem label="Start date" value={formatDate(String(form.start_date))} />
              <DetailItem label="End date" value={formatDate(String(form.end_date))} />
              <DetailItem label="Interest rate" value={`${form.interest_rate || 0}% p.a.`} />
              <DetailItem label="Tenure" value={`${form.tenure_months || "—"} months`} />
            </DetailGrid>
          </DetailSection>

          <DetailSection
            title="Guarantee"
            description="Guarantor on record"
            defaultExpanded={false}
          >
            <DetailGrid>
              <DetailItem label="Guarantor" value={guarantorLabel} fullWidth />
            </DetailGrid>
          </DetailSection>

          <DetailSection title="Purpose" defaultExpanded={false}>
            <DetailItem
              label="Notes"
              value={form.purpose || "—"}
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
        title={title}
        subtitle={
          mode === "create"
            ? "Principal, rate and tenure drive EMI; outstanding tracks repayment status"
            : "Update fields and save changes"
        }
        backHref={BASE}
        mode={mode}
        loading={loading}
        saving={saving}
        onSubmit={save}
        extraActions={null}
      >
        <Stack spacing={2}>
          <DetailSection title="Borrower" defaultExpanded>
            <Stack spacing={2}>
              <TextField
                label="Loan number"
                required
                fullWidth
                value={form.loan_number}
                disabled={readOnly}
                helperText="Auto-generated · editable"
                placeholder="LN-YYYY-#####"
                onChange={(e) => setForm({ ...form, loan_number: e.target.value })}
              />
              <RelationSelect
                label="Employee"
                required
                value={form.employee}
                disabled={readOnly}
                relation={RELATIONS.employee}
                onChange={(v) => setForm({ ...form, employee: v })}
              />
              <TextField
                select
                label="Loan type"
                fullWidth
                value={form.loan_type}
                disabled={readOnly}
                onChange={(e) => setForm({ ...form, loan_type: e.target.value })}
              >
                {LOAN_TYPES.map((t) => (
                  <MenuItem key={t} value={t}>
                    {t.replace("_", " ")}
                  </MenuItem>
                ))}
              </TextField>
              <RelationSelect
                label="Currency"
                required
                value={form.currency}
                disabled={readOnly}
                relation={RELATIONS.currency}
                onChange={(v) => setForm({ ...form, currency: v })}
              />
              <TextField
                select
                label="Status"
                fullWidth
                helperText="draft → pending → approved → active (payroll EMI) → closed"
                value={form.status}
                disabled={readOnly}
                onChange={(e) => setForm({ ...form, status: e.target.value })}
              >
                {LOAN_STATUSES.map((s) => (
                  <MenuItem key={s} value={s}>
                    {s}
                  </MenuItem>
                ))}
              </TextField>
            </Stack>
          </DetailSection>
          <DetailSection title="Amounts & schedule" defaultExpanded>
            <Stack spacing={2}>
              <TextField
                label="Principal"
                type="number"
                required
                fullWidth
                value={form.principal}
                disabled={readOnly}
                onChange={(e) => {
                  const principal = e.target.value;
                  setForm({
                    ...form,
                    principal,
                    outstanding_balance:
                      mode === "create" ? principal : form.outstanding_balance,
                  });
                }}
              />
              <TextField
                label="Interest rate % (annual)"
                type="number"
                fullWidth
                value={form.interest_rate}
                disabled={readOnly}
                onChange={(e) => setForm({ ...form, interest_rate: e.target.value })}
              />
              <TextField
                label="Tenure (months)"
                type="number"
                fullWidth
                value={form.tenure_months}
                disabled={readOnly}
                onChange={(e) => setForm({ ...form, tenure_months: e.target.value })}
              />
              <Stack direction="row" spacing={1} alignItems="flex-start">
                <TextField
                  label="Monthly installment (EMI)"
                  type="number"
                  fullWidth
                  helperText={
                    calcHint ||
                    "EMI auto-updates when principal, rate or tenure change"
                  }
                  value={form.monthly_installment}
                  disabled={readOnly || calcBusy}
                  onChange={(e) =>
                    setForm({ ...form, monthly_installment: e.target.value })
                  }
                />
                <Button
                  variant="outlined"
                  startIcon={<CalculateIcon />}
                  disabled={calcBusy}
                  sx={{ mt: 0.5, whiteSpace: "nowrap" }}
                  onClick={() => recalculateEmi()}
                >
                  {calcBusy ? "Calculating…" : "Recalculate"}
                </Button>
              </Stack>
              <TextField
                label="Outstanding amount"
                type="number"
                fullWidth
                helperText="Remaining balance; starts at principal and reduces with repayments"
                value={form.outstanding_balance}
                disabled={readOnly}
                onChange={(e) =>
                  setForm({ ...form, outstanding_balance: e.target.value })
                }
              />
              <DateTextField
                label="Start date"
                value={form.start_date}
                disabled={readOnly}
                onChange={(e) => setForm({ ...form, start_date: e.target.value })}
              />
              <DateTextField
                label="End date"
                value={form.end_date}
                disabled={readOnly}
                notBefore={form.start_date}
                helperText="Auto-set from start date + tenure months"
                onChange={(e) => setForm({ ...form, end_date: e.target.value })}
              />
            </Stack>
          </DetailSection>
          <DetailSection title="Guarantee & purpose" defaultExpanded={false}>
            <Stack spacing={2}>
              <RelationSelect
                label="Guarantee (guarantor)"
                value={form.guarantor}
                disabled={readOnly}
                helperText="Employee who guarantees this loan"
                relation={{
                  ...RELATIONS.employee,
                  allowClear: true,
                  clearLabel: "— None —",
                }}
                onChange={(v) => {
                  const g = employees.find((x) => String(x.id) === v);
                  setForm({
                    ...form,
                    guarantor: v,
                    guarantor_name: g
                      ? `${g.first_name} ${g.last_name}`.trim()
                      : "",
                  });
                }}
              />
              {form.guarantor_name && !form.guarantor ? (
                <Typography variant="caption" color="text.secondary">
                  Legacy guarantor text: {form.guarantor_name}
                </Typography>
              ) : null}
              <TextField
                label="Purpose"
                multiline
                minRows={2}
                fullWidth
                value={form.purpose}
                disabled={readOnly}
                onChange={(e) => setForm({ ...form, purpose: e.target.value })}
              />
              <TextField
                select
                label="Deduct from payroll"
                fullWidth
                value={form.deduct_from_payroll ? "yes" : "no"}
                disabled={readOnly}
                onChange={(e) =>
                  setForm({
                    ...form,
                    deduct_from_payroll: e.target.value === "yes",
                  })
                }
              >
                <MenuItem value="yes">Yes</MenuItem>
                <MenuItem value="no">No</MenuItem>
              </TextField>
            </Stack>
          </DetailSection>
        </Stack>
      </FormPageShell>
    </ModuleGate>
  );
}
