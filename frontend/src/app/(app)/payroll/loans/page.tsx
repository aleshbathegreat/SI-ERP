"use client";

import { useMemo, useState } from "react";
import {
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Stack,
  Typography,
} from "@mui/material";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import DoneAllIcon from "@mui/icons-material/DoneAll";
import { useSnackbar } from "notistack";
import CrudTable from "@/components/crud/CrudTable";
import ConfirmDialog from "@/components/crud/ConfirmDialog";
import ModuleGate from "@/components/ModuleGate";
import PageHeader from "@/components/PageHeader";
import WorkflowActions from "@/components/WorkflowActions";
import { useCrudList } from "@/hooks/useCrudList";
import { usePermissions } from "@/hooks/usePermissions";
import { formatDate, formatMoney } from "@/lib/format";
import api from "@/lib/api";

type Loan = {
  id: number;
  loan_number: string;
  employee: number;
  employee_name?: string;
  employee_code?: string;
  loan_type: string;
  currency: string;
  principal: string | number;
  interest_rate: string | number;
  tenure_months: number;
  monthly_installment: string | number;
  outstanding_balance: string | number;
  total_repaid: string | number;
  start_date?: string | null;
  end_date?: string | null;
  status: string;
  purpose: string;
  guarantor?: number | null;
  guarantor_name: string;
  guarantor_employee_name?: string;
  deduct_from_payroll: boolean;
};

const statusColor = (s: string): "default" | "info" | "warning" | "success" | "error" => {
  if (s === "draft" || s === "pending") return "info";
  if (s === "approved") return "warning";
  if (s === "active") return "success";
  if (s === "closed") return "default";
  if (s === "rejected" || s === "written_off") return "error";
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

export default function EmployeeLoansPage() {
  const moduleKey = "payroll.loans";
  const { canAdd, canChange, canDelete } = usePermissions();
  const { enqueueSnackbar } = useSnackbar();
  const crud = useCrudList<Loan>("/payroll/loans/", "Employee loan", "/payroll/loans");
  const [busyId, setBusyId] = useState<number | null>(null);

  const kpis = useMemo(() => {
    const rows = crud.rows;
    return {
      count: rows.length,
      active: rows.filter((r) => r.status === "active").length,
      principal: rows.reduce((a, r) => a + (Number(r.principal) || 0), 0),
      outstanding: rows.reduce((a, r) => a + (Number(r.outstanding_balance) || 0), 0),
    };
  }, [crud.rows]);

  const activate = async (id: number) => {
    setBusyId(id);
    try {
      await api.post(`/payroll/loans/${id}/activate/`);
      enqueueSnackbar("Loan activated — payroll deduction enabled", { variant: "success" });
      await crud.load();
    } catch (e: unknown) {
      const msg =
        (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        "Activate failed";
      enqueueSnackbar(String(msg), { variant: "error" });
    } finally {
      setBusyId(null);
    }
  };

  return (
    <ModuleGate module={moduleKey}>
      <Box>
        <PageHeader
          title="Employee loans"
          subtitle="Advances & loans with EMI schedule and payroll deduction"
          moduleKey={moduleKey}
        />
        {!crud.loading && crud.rows.length > 0 ? (
          <Stack direction="row" spacing={1.5} flexWrap="wrap" useFlexGap sx={{ mb: 2 }}>
            <Kpi label="Loans" value={String(kpis.count)} />
            <Kpi label="Active" value={String(kpis.active)} />
            <Kpi label="Principal" value={formatMoney(kpis.principal)} />
            <Kpi label="Outstanding" value={formatMoney(kpis.outstanding)} />
          </Stack>
        ) : null}
        <CrudTable
          title="Employee loans & advances"
          subtitle="Personal, housing, vehicle, salary advance — deducted on payslip"
          rows={crud.rows}
          loading={crud.loading}
          selectedIds={crud.selectedIds}
          onToggleAll={crud.toggleAll}
          onToggleOne={crud.toggleOne}
          onRefresh={crud.load}
          onCreate={crud.openCreate}
          onEdit={crud.openEdit}
          onView={crud.openView}
          onDeleteOne={crud.askDeleteOne}
          onBulkDelete={crud.askBulkDelete}
          createLabel="New loan"
          canCreate={canAdd(moduleKey)}
          canEdit={canChange(moduleKey)}
          canDelete={canDelete(moduleKey)}
          emptyTitle="No employee loans"
          emptyHint="Create a loan, approve, then Activate to deduct EMI on payroll runs."
          columns={[
            { key: "no", header: "Loan #", render: (r) => r.loan_number },
            {
              key: "emp",
              header: "Employee",
              render: (r) =>
                `${r.employee_code || ""} ${r.employee_name || ""}`.trim() || String(r.employee),
            },
            { key: "type", header: "Type", render: (r) => r.loan_type.replace("_", " ") },
            {
              key: "principal",
              header: "Principal",
              render: (r) => formatMoney(r.principal, r.currency),
            },
            {
              key: "emi",
              header: "EMI",
              render: (r) => formatMoney(r.monthly_installment, r.currency),
            },
            {
              key: "out",
              header: "Outstanding",
              render: (r) => formatMoney(r.outstanding_balance, r.currency),
            },
            {
              key: "guarantor",
              header: "Guarantor",
              render: (r) =>
                r.guarantor_employee_name || r.guarantor_name || "—",
            },
            { key: "start", header: "Start", render: (r) => formatDate(r.start_date) },
            {
              key: "status",
              header: "Status / LoA",
              render: (r) => (
                <Stack spacing={0.5}>
                  <Chip size="small" color={statusColor(r.status)} label={r.status} />
                  <WorkflowActions
                    resourcePath="/payroll/loans/"
                    id={r.id}
                    status={r.status}
                    moduleKey={moduleKey}
                    onDone={crud.load}
                  />
                  {canChange(moduleKey) && (r.status === "approved" || r.status === "draft") ? (
                    <Button
                      size="small"
                      startIcon={<PlayArrowIcon />}
                      disabled={busyId === r.id}
                      onClick={() => activate(r.id)}
                    >
                      Activate
                    </Button>
                  ) : null}
                  {canChange(moduleKey) && r.status === "active" ? (
                    <Button
                      size="small"
                      startIcon={<DoneAllIcon />}
                      disabled={busyId === r.id}
                      onClick={async () => {
                        setBusyId(r.id);
                        try {
                          await api.post(`/payroll/loans/${r.id}/close/`);
                          enqueueSnackbar("Loan closed", { variant: "success" });
                          await crud.load();
                        } finally {
                          setBusyId(null);
                        }
                      }}
                    >
                      Close
                    </Button>
                  ) : null}
                </Stack>
              ),
            },
          ]}
        />
        <ConfirmDialog
          open={!!crud.confirm}
          title={crud.confirm?.type === "bulk" ? "Delete selected loans?" : "Delete loan?"}
          message={
            crud.confirm?.type === "bulk"
              ? `Permanently delete ${crud.selectedIds.length} loan(s)?`
              : `Delete loan “${crud.confirm?.row?.loan_number}”?`
          }
          confirmLabel="Delete"
          loading={crud.saving}
          onClose={() => crud.setConfirm(null)}
          onConfirm={crud.runConfirmDelete}
        />
      </Box>
    </ModuleGate>
  );
}
