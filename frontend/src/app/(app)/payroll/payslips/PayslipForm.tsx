"use client";

import Link from "next/link";
import { Button, MenuItem, Stack, TextField } from "@mui/material";
import EditIcon from "@mui/icons-material/Edit";
import FormPageShell from "@/components/crud/FormPageShell";
import { DetailSection } from "@/components/crud/DetailPageShell";
import RelationSelect, { RELATIONS } from "@/components/crud/RelationSelect";
import ModuleGate from "@/components/ModuleGate";
import { useEntityForm, type FormMode } from "@/hooks/useEntityForm";
import { usePermissions } from "@/hooks/usePermissions";
import {
  FIELD_LABELS,
  moneyFields,
  recomputeNet,
  slipEmpty,
  type MoneyKey,
} from "./payslipHelpers";

const BASE = "/payroll/payslips";
const MODULE = "payroll.payslips";
const API = "/payroll/payslips/";

function n(v: string | number | undefined) {
  return Number(v ?? 0) || 0;
}

export default function PayslipForm({ mode, id }: { mode: FormMode; id?: string }) {
  const { canChange } = usePermissions();

  const { form, setForm, loading, saving, save, readOnly } = useEntityForm({
    resourcePath: API,
    entityLabel: "Payslip",
    basePath: "/payroll",
    mode,
    id,
    empty: { ...slipEmpty },
    mapLoaded: (a) => {
      const next: Record<string, string> = {
        ...slipEmpty,
        period: String(a.period ?? ""),
        employee: String(a.employee ?? ""),
        currency: String(a.currency || "PKR"),
        payment_method: String(a.payment_method || "bank_transfer"),
        bank_account: String(a.bank_account || ""),
        payment_reference: String(a.payment_reference || ""),
        payment_date: String(a.payment_date || ""),
        remarks: String(a.remarks || ""),
        days_worked: String(a.days_worked ?? "30"),
        unpaid_leave_days: String(a.unpaid_leave_days ?? "0"),
        overtime_hours: String(a.overtime_hours ?? "0"),
      };
      for (const f of moneyFields) {
        const v =
          a[f] ??
          (f === "income_tax" ? a.tax : f === "eobi" ? a.eobi : 0);
        next[f] = String(v ?? "0");
      }
      if (!n(next.income_tax) && a.tax) next.income_tax = String(a.tax);
      return recomputeNet(next);
    },
    mapPayload: (f) => {
      const netted = recomputeNet(f);
      const payload: Record<string, unknown> = {
        period: Number(netted.period),
        employee: Number(netted.employee),
        currency: netted.currency,
        payment_method: netted.payment_method,
        bank_account: netted.bank_account,
        payment_reference: netted.payment_reference,
        payment_date: netted.payment_date || null,
        remarks: netted.remarks,
        days_worked: netted.days_worked,
        unpaid_leave_days: netted.unpaid_leave_days,
        overtime_hours: netted.overtime_hours,
        tax: netted.income_tax,
        eobi: netted.eobi,
      };
      for (const field of moneyFields) payload[field] = netted[field];
      return payload;
    },
  });

  const title =
    mode === "create" ? "Add payslip" : mode === "edit" ? "Edit payslip" : "View payslip";

  return (
    <ModuleGate module={MODULE}>
      <FormPageShell
        title={title}
        subtitle="Earnings, statutory deductions, and payment"
        backHref="/payroll"
        backLabel="Back to payroll"
        mode={mode}
        loading={loading}
        saving={saving}
        onSubmit={save}
        maxWidth={720}
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
        <Stack spacing={2}>
          <DetailSection title="Employee & period" defaultExpanded>
            <Stack spacing={2}>
              <RelationSelect
                label="Period"
                required
                value={form.period}
                disabled={readOnly}
                relation={RELATIONS.payrollPeriod}
                onChange={(v) => setForm({ ...form, period: v })}
              />
              <RelationSelect
                label="Employee"
                required
                value={form.employee}
                disabled={readOnly}
                relation={RELATIONS.employee}
                onChange={(v) => setForm({ ...form, employee: v })}
              />
              <TextField label="Gross pay" fullWidth value={form.gross_pay} disabled />
              <TextField label="Net pay" fullWidth value={form.net_pay} disabled />
            </Stack>
          </DetailSection>

          <DetailSection title="Earnings" defaultExpanded={mode !== "view"}>
            <Stack spacing={2}>
              {(
                [
                  "basic",
                  "housing_allowance",
                  "transport_allowance",
                  "medical_allowance",
                  "meal_allowance",
                  "overtime",
                  "bonus",
                  "commission",
                  "other_earnings",
                ] as MoneyKey[]
              ).map((field) => (
                <TextField
                  key={field}
                  label={FIELD_LABELS[field]}
                  type="number"
                  fullWidth
                  value={form[field]}
                  disabled={readOnly}
                  onChange={(e) =>
                    setForm(recomputeNet({ ...form, [field]: e.target.value }))
                  }
                />
              ))}
            </Stack>
          </DetailSection>

          <DetailSection title="Deductions & statutory" defaultExpanded={false}>
            <Stack spacing={2}>
              {(
                [
                  "income_tax",
                  "eobi",
                  "provident_fund",
                  "pension",
                  "loan_repayment",
                  "advance_recovery",
                  "other_deductions",
                  "employer_provident_fund",
                ] as MoneyKey[]
              ).map((field) => (
                <TextField
                  key={field}
                  label={FIELD_LABELS[field]}
                  type="number"
                  fullWidth
                  value={form[field]}
                  disabled={readOnly}
                  onChange={(e) =>
                    setForm(recomputeNet({ ...form, [field]: e.target.value }))
                  }
                />
              ))}
            </Stack>
          </DetailSection>

          <DetailSection title="Attendance & payment" defaultExpanded={false}>
            <Stack spacing={2}>
              <TextField
                label={FIELD_LABELS.days_worked}
                type="number"
                fullWidth
                value={form.days_worked}
                disabled={readOnly}
                onChange={(e) => setForm({ ...form, days_worked: e.target.value })}
              />
              <TextField
                label={FIELD_LABELS.unpaid_leave_days}
                type="number"
                fullWidth
                value={form.unpaid_leave_days}
                disabled={readOnly}
                onChange={(e) =>
                  setForm({ ...form, unpaid_leave_days: e.target.value })
                }
              />
              <TextField
                label={FIELD_LABELS.overtime_hours}
                type="number"
                fullWidth
                value={form.overtime_hours}
                disabled={readOnly}
                onChange={(e) =>
                  setForm({ ...form, overtime_hours: e.target.value })
                }
              />
              <TextField
                select
                label="Payment method"
                fullWidth
                value={form.payment_method}
                disabled={readOnly}
                onChange={(e) =>
                  setForm({ ...form, payment_method: e.target.value })
                }
              >
                {["bank_transfer", "cash", "cheque", "wallet"].map((m) => (
                  <MenuItem key={m} value={m}>
                    {m.replace("_", " ")}
                  </MenuItem>
                ))}
              </TextField>
              <TextField
                label="Bank account / IBAN"
                fullWidth
                value={form.bank_account}
                disabled={readOnly}
                onChange={(e) => setForm({ ...form, bank_account: e.target.value })}
              />
              <TextField
                label="Payment reference"
                fullWidth
                value={form.payment_reference}
                disabled={readOnly}
                onChange={(e) =>
                  setForm({ ...form, payment_reference: e.target.value })
                }
              />
              <TextField
                label="Payment date"
                type="date"
                fullWidth
                InputLabelProps={{ shrink: true }}
                value={form.payment_date}
                disabled={readOnly}
                onChange={(e) => setForm({ ...form, payment_date: e.target.value })}
              />
              <RelationSelect
                label="Currency"
                required
                value={form.currency}
                disabled={readOnly}
                relation={RELATIONS.currency}
                onChange={(v) => setForm({ ...form, currency: v })}
              />
              <TextField
                label="Remarks"
                multiline
                minRows={2}
                fullWidth
                value={form.remarks}
                disabled={readOnly}
                onChange={(e) => setForm({ ...form, remarks: e.target.value })}
              />
            </Stack>
          </DetailSection>
        </Stack>
      </FormPageShell>
    </ModuleGate>
  );
}
