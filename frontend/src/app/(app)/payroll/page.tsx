"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Dialog,
  DialogContent,
  DialogTitle,
  MenuItem,
  Stack,
  Tab,
  Tabs,
  TextField,
  Typography,
} from "@mui/material";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import DoneAllIcon from "@mui/icons-material/DoneAll";
import PaymentsIcon from "@mui/icons-material/Payments";
import EmailIcon from "@mui/icons-material/Email";
import { useSnackbar } from "notistack";
import CrudTable from "@/components/crud/CrudTable";
import ConfirmDialog from "@/components/crud/ConfirmDialog";
import ModuleGate from "@/components/ModuleGate";
import { useCrudList } from "@/hooks/useCrudList";
import { usePermissions } from "@/hooks/usePermissions";
import { formatMoney } from "@/lib/format";
import api from "@/lib/api";

type Period = {
  id: number;
  name: string;
  year: number;
  month: number;
  status: string;
  pay_date?: string | null;
  currency?: string;
  notes?: string;
  gl_journal?: number | null;
};

type Payslip = {
  id: number;
  period: number;
  period_name?: string;
  employee: number;
  employee_name?: string;
  employee_code?: string;
  currency?: string;
  basic: string | number;
  housing_allowance?: string | number;
  transport_allowance?: string | number;
  medical_allowance?: string | number;
  meal_allowance?: string | number;
  overtime?: string | number;
  bonus?: string | number;
  commission?: string | number;
  other_earnings?: string | number;
  allowances: string | number;
  income_tax?: string | number;
  tax: string | number;
  social_security?: string | number;
  eobi: string | number;
  provident_fund?: string | number;
  pension?: string | number;
  loan_repayment?: string | number;
  advance_recovery?: string | number;
  other_deductions?: string | number;
  deductions: string | number;
  employer_provident_fund?: string | number;
  gross_pay?: string | number;
  total_deductions?: string | number;
  employer_cost?: string | number;
  net_pay: string | number;
  days_worked?: string | number;
  unpaid_leave_days?: string | number;
  overtime_hours?: string | number;
  payment_method?: string;
  bank_account?: string;
  payment_reference?: string;
  payment_date?: string | null;
  remarks?: string;
};

type PeriodSummary = {
  slip_count: number;
  total_basic: string;
  total_gross?: string;
  total_allowances: string;
  total_deductions: string;
  total_tax: string;
  total_eobi: string;
  total_pf?: string;
  total_loans?: string;
  total_net: string;
  total_employer_cost?: string;
};

const statusColor = (s: string): "default" | "info" | "warning" | "success" | "error" => {
  if (s === "open") return "default";
  if (s === "processing") return "info";
  if (s === "approved") return "warning";
  if (s === "paid") return "success";
  if (s === "closed") return "error";
  return "default";
};

function Kpi({ label, value }: { label: string; value: string }) {
  return (
    <Card variant="outlined" sx={{ flex: 1, minWidth: 140 }}>
      <CardContent sx={{ py: 1.5, "&:last-child": { pb: 1.5 } }}>
        <Typography variant="caption" color="text.secondary">
          {label}
        </Typography>
        <Typography variant="h6" fontWeight={700}>
          {value}
        </Typography>
      </CardContent>
    </Card>
  );
}

export default function PayrollPage() {
  const router = useRouter();
  const { canAdd, canChange, canDelete, canView } = usePermissions();
  const { enqueueSnackbar } = useSnackbar();
  const [tab, setTab] = useState(0);
  const periods = useCrudList<Period>(
    "/payroll/periods/",
    "Payroll period",
    "/payroll/periods"
  );
  const slips = useCrudList<Payslip>(
    "/payroll/payslips/",
    "Payslip",
    "/payroll/payslips"
  );
  const [periodFilter, setPeriodFilter] = useState<string>("");
  const [summary, setSummary] = useState<PeriodSummary | null>(null);
  const [statutory, setStatutory] = useState<Record<string, string> | null>(null);
  const [certificate, setCertificate] = useState<Record<string, string> | null>(null);
  const [busy, setBusy] = useState(false);

  const filteredSlips = useMemo(() => {
    if (!periodFilter) return slips.rows;
    return slips.rows.filter((r) => String(r.period) === periodFilter);
  }, [slips.rows, periodFilter]);

  const selectedPeriod = useMemo(
    () => periods.rows.find((p) => String(p.id) === periodFilter) || periods.rows[0] || null,
    [periods.rows, periodFilter]
  );

  useEffect(() => {
    if (!periods.rows.length) return;
    if (!periodFilter) setPeriodFilter(String(periods.rows[0].id));
  }, [periods.rows, periodFilter]);

  useEffect(() => {
    const id = periodFilter || (selectedPeriod ? String(selectedPeriod.id) : "");
    if (!id) {
      setSummary(null);
      return;
    }
    api
      .get<PeriodSummary>(`/payroll/periods/${id}/summary/`)
      .then((r) => setSummary(r.data))
      .catch(() => setSummary(null));
  }, [periodFilter, selectedPeriod, slips.rows]);

  const runPeriodAction = async (
    action: "submit" | "approve" | "reject" | "mark_paid" | "generate" | "email" | "post_gl"
  ) => {
    if (!selectedPeriod) return;
    setBusy(true);
    try {
      if (action === "generate") {
        const { data } = await api.post<{
          created: number;
          updated: number;
          loans_applied: number;
        }>(`/payroll/periods/${selectedPeriod.id}/generate-payslips/`);
        enqueueSnackbar(
          `Payslips: ${data.created} created, ${data.updated} updated · ${data.loans_applied} loan EMI(s)`,
          { variant: "success" }
        );
      } else if (action === "email") {
        const { data } = await api.post<{
          sent: number;
          failed: number;
          skipped: number;
        }>(`/payroll/periods/${selectedPeriod.id}/send-payslips/`);
        enqueueSnackbar(
          `Payslip emails · sent ${data.sent}, failed ${data.failed}, skipped ${data.skipped}`,
          { variant: data.sent > 0 ? "success" : "warning" }
        );
      } else if (action === "post_gl") {
        const { data } = await api.post<{
          journal_id: number;
          reference: string;
          gross: string;
        }>(`/payroll/periods/${selectedPeriod.id}/post-to-gl/`);
        enqueueSnackbar(
          `Posted to GL journal #${data.journal_id} (${data.reference}) · gross ${data.gross}`,
          { variant: "success" }
        );
      } else {
        await api.post(`/payroll/periods/${selectedPeriod.id}/${action}/`);
        enqueueSnackbar(`Period ${action.replace("_", " ")} succeeded`, { variant: "success" });
      }
      await periods.load();
      await slips.load();
    } catch (e: unknown) {
      const msg =
        (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        "Action failed";
      enqueueSnackbar(String(msg), { variant: "error" });
    } finally {
      setBusy(false);
    }
  };

  return (
    <ModuleGate module={canView("payroll.periods") ? "payroll.periods" : "payroll.payslips"}>
      <Box>
        <Stack
          direction={{ xs: "column", md: "row" }}
          justifyContent="space-between"
          alignItems={{ xs: "stretch", md: "center" }}
          spacing={2}
          sx={{ mb: 2 }}
        >
          <Box>
            <Typography variant="h4">Payroll runs</Typography>
            <Typography variant="body2" color="text.secondary">
              International payslip register · statutory · loans · payment
            </Typography>
          </Box>
          <TextField
            select
            size="small"
            label="Active period"
            value={periodFilter}
            onChange={(e) => setPeriodFilter(e.target.value)}
            sx={{ minWidth: 220 }}
          >
            {periods.rows.map((p) => (
              <MenuItem key={p.id} value={String(p.id)}>
                {p.name} ({p.status})
              </MenuItem>
            ))}
          </TextField>
        </Stack>

        {summary ? (
          <Stack direction="row" spacing={1.5} flexWrap="wrap" useFlexGap sx={{ mb: 2 }}>
            <Kpi label="Slips" value={String(summary.slip_count)} />
            <Kpi label="Gross" value={formatMoney(summary.total_gross || summary.total_basic)} />
            <Kpi label="Tax" value={formatMoney(summary.total_tax)} />
            <Kpi label="EOBI" value={formatMoney(summary.total_eobi)} />
            <Kpi label="PF" value={formatMoney(summary.total_pf || 0)} />
            <Kpi label="Loans" value={formatMoney(summary.total_loans || 0)} />
            <Kpi label="Net payroll" value={formatMoney(summary.total_net)} />
          </Stack>
        ) : null}

        {selectedPeriod && canChange("payroll.periods") ? (
          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ mb: 2 }}>
            <Button
              variant="contained"
              startIcon={<PlayArrowIcon />}
              disabled={busy}
              onClick={() => runPeriodAction("generate")}
            >
              Generate / refresh payslips
            </Button>
            <Button disabled={busy || selectedPeriod.status !== "open"} onClick={() => runPeriodAction("submit")}>
              Submit for processing
            </Button>
            <Button
              disabled={busy || selectedPeriod.status !== "processing"}
              onClick={() => runPeriodAction("approve")}
            >
              Approve
            </Button>
            <Button
              disabled={busy || !["processing", "approved"].includes(selectedPeriod.status)}
              onClick={() => runPeriodAction("reject")}
            >
              Re-open
            </Button>
            <Button
              variant="outlined"
              color="success"
              startIcon={<PaymentsIcon />}
              disabled={busy || selectedPeriod.status !== "approved"}
              onClick={() => runPeriodAction("mark_paid")}
            >
              Mark paid (apply loans)
            </Button>
            <Button
              variant="outlined"
              startIcon={<EmailIcon />}
              disabled={busy || !filteredSlips.length}
              onClick={() => runPeriodAction("email")}
            >
              Email payslips
            </Button>
            <Button
              variant="outlined"
              color="secondary"
              disabled={
                busy ||
                !["approved", "paid"].includes(selectedPeriod.status) ||
                !!selectedPeriod.gl_journal
              }
              onClick={() => runPeriodAction("post_gl")}
            >
              Post to GL
            </Button>
            <Button
              variant="outlined"
              disabled={busy || !filteredSlips.length}
              onClick={async () => {
                try {
                  const res = await api.get(`/payroll/periods/${selectedPeriod.id}/bank-advice/`, {
                    responseType: "blob",
                  });
                  const url = URL.createObjectURL(res.data);
                  const a = document.createElement("a");
                  a.href = url;
                  a.download = `Bank_Advice_${selectedPeriod.year}_${selectedPeriod.month}.csv`;
                  a.click();
                  URL.revokeObjectURL(url);
                } catch {
                  enqueueSnackbar("Bank advice failed", { variant: "error" });
                }
              }}
            >
              Bank advice
            </Button>
            <Button
              variant="outlined"
              disabled={busy}
              onClick={async () => {
                try {
                  const { data } = await api.get<Record<string, string>>(
                    `/payroll/periods/${selectedPeriod.id}/statutory/`
                  );
                  setStatutory(data);
                } catch {
                  enqueueSnackbar("Statutory register failed", { variant: "error" });
                }
              }}
            >
              Tax & EOBI
            </Button>
            <Chip
              icon={<DoneAllIcon />}
              color={statusColor(selectedPeriod.status)}
              label={`Period: ${selectedPeriod.status}`}
            />
          </Stack>
        ) : null}

        <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 2 }}>
          <Tab label="Periods" />
          <Tab label="Payslips" />
        </Tabs>

        {tab === 0 ? (
          <>
            <CrudTable
              title="Payroll periods"
              subtitle="Monthly runs with LoA workflow"
              rows={periods.rows}
              loading={periods.loading}
              selectedIds={periods.selectedIds}
              onToggleAll={periods.toggleAll}
              onToggleOne={periods.toggleOne}
              onRefresh={periods.load}
              onCreate={periods.openCreate}
              onEdit={periods.openEdit}
              onView={periods.openView}
              onDeleteOne={periods.askDeleteOne}
              onBulkDelete={periods.askBulkDelete}
              createLabel="Add period"
              canCreate={canAdd("payroll.periods")}
              canEdit={canChange("payroll.periods")}
              canDelete={canDelete("payroll.periods")}
              emptyTitle="No payroll periods"
              emptyHint="Create a period, then generate payslips."
              columns={[
                { key: "name", header: "Name", render: (r) => r.name },
                { key: "ym", header: "Year / Month", render: (r) => `${r.year}-${String(r.month).padStart(2, "0")}` },
                {
                  key: "status",
                  header: "Status",
                  render: (r) => (
                    <Chip size="small" color={statusColor(r.status)} label={r.status} />
                  ),
                },
              ]}
            />
            <ConfirmDialog
              open={!!periods.confirm}
              title={periods.confirm?.type === "bulk" ? "Delete selected periods?" : "Delete period?"}
              message={
                periods.confirm?.type === "bulk"
                  ? `Permanently delete ${periods.selectedIds.length} period(s)?`
                  : `Delete period “${periods.confirm?.row?.name}”?`
              }
              confirmLabel="Delete"
              loading={periods.saving}
              onClose={() => periods.setConfirm(null)}
              onConfirm={periods.runConfirmDelete}
            />
          </>
        ) : (
          <>
            <CrudTable
              title="Payslips"
              subtitle={
                selectedPeriod
                  ? `${selectedPeriod.name} · ${filteredSlips.length} slip(s)`
                  : "Employee payslips"
              }
              rows={filteredSlips}
              loading={slips.loading}
              selectedIds={slips.selectedIds}
              onToggleAll={slips.toggleAll}
              onToggleOne={slips.toggleOne}
              onRefresh={slips.load}
              onCreate={() =>
                router.push(
                  `/payroll/payslips/new${periodFilter ? `?period=${periodFilter}` : ""}`
                )
              }
              onEdit={slips.openEdit}
              onView={slips.openView}
              onDeleteOne={slips.askDeleteOne}
              onBulkDelete={slips.askBulkDelete}
              createLabel="Add payslip"
              canCreate={canAdd("payroll.payslips")}
              canEdit={canChange("payroll.payslips")}
              canDelete={canDelete("payroll.payslips")}
              emptyTitle="No payslips for this period"
              emptyHint="Use Generate payslips, or add one manually with full earnings/deductions."
              columns={[
                {
                  key: "emp",
                  header: "Employee",
                  render: (r) => (
                    <Stack direction="row" spacing={1} alignItems="center">
                      <span>
                        {`${r.employee_code || ""} ${r.employee_name || ""}`.trim() ||
                          String(r.employee)}
                      </span>
                      <Button
                        size="small"
                        onClick={async () => {
                          try {
                            const { data } = await api.get<Record<string, string>>(
                              "/payroll/payslips/tax-certificate/",
                              { params: { employee: r.employee } }
                            );
                            setCertificate(data);
                          } catch {
                            enqueueSnackbar("Tax certificate failed", { variant: "error" });
                          }
                        }}
                      >
                        Certificate
                      </Button>
                    </Stack>
                  ),
                },
                { key: "gross", header: "Gross", render: (r) => formatMoney(r.gross_pay ?? r.basic) },
                { key: "tax", header: "Tax", render: (r) => formatMoney(r.income_tax ?? r.tax) },
                { key: "pf", header: "PF", render: (r) => formatMoney(r.provident_fund) },
                { key: "loan", header: "Loan", render: (r) => formatMoney(r.loan_repayment) },
                { key: "net", header: "Net pay", render: (r) => formatMoney(r.net_pay) },
              ]}
            />
            <ConfirmDialog
              open={!!slips.confirm}
              title={slips.confirm?.type === "bulk" ? "Delete selected payslips?" : "Delete payslip?"}
              message={
                slips.confirm?.type === "bulk"
                  ? `Permanently delete ${slips.selectedIds.length} payslip(s)?`
                  : `Delete payslip for ${slips.confirm?.row?.employee_name || "employee"}?`
              }
              confirmLabel="Delete"
              loading={slips.saving}
              onClose={() => slips.setConfirm(null)}
              onConfirm={slips.runConfirmDelete}
            />
          </>
        )}
        <Dialog open={!!statutory} onClose={() => setStatutory(null)} fullWidth maxWidth="xs">
          <DialogTitle>Tax and EOBI</DialogTitle>
          <DialogContent>
            <Typography variant="body2">{statutory?.period_name}</Typography>
            <Typography>Income tax withheld {statutory?.income_tax}</Typography>
            <Typography>EOBI employee {statutory?.eobi_employee}</Typography>
            <Typography>EOBI employer {statutory?.eobi_employer}</Typography>
            <Typography fontWeight={700}>EOBI payable {statutory?.eobi_payable}</Typography>
          </DialogContent>
        </Dialog>
        <Dialog open={!!certificate} onClose={() => setCertificate(null)} fullWidth maxWidth="sm">
          <DialogTitle>Tax certificate {certificate?.fiscal_year}</DialogTitle>
          <DialogContent>
            <Typography fontWeight={700}>{certificate?.employee_name}</Typography>
            <Typography variant="body2" color="text.secondary">
              {certificate?.organization} · {certificate?.period_from} to {certificate?.period_to}
            </Typography>
            <Typography sx={{ mt: 1 }}>Gross {certificate?.total_gross}</Typography>
            <Typography>Tax withheld {certificate?.total_tax}</Typography>
            <Typography>Net {certificate?.total_net}</Typography>
          </DialogContent>
        </Dialog>
      </Box>
    </ModuleGate>
  );
}
