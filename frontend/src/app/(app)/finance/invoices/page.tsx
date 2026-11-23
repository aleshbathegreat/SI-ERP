"use client";

import { useMemo } from "react";
import {
  Box,
  Card,
  CardContent,
  Chip,
  Stack,
  Typography,
} from "@mui/material";
import CrudTable from "@/components/crud/CrudTable";
import ConfirmDialog from "@/components/crud/ConfirmDialog";
import WorkflowActions from "@/components/WorkflowActions";
import ModuleGate from "@/components/ModuleGate";
import PageHeader from "@/components/PageHeader";
import { useCrudList } from "@/hooks/useCrudList";
import { usePermissions } from "@/hooks/usePermissions";
import { formatDate, formatMoney } from "@/lib/format";
import { humanizeStatus } from "@/lib/financeLabels";

type Row = {
  id: number;
  vendor_name?: string;
  vendor: string | number;
  invoice_no: string | number;
  invoice_date: string | number;
  due_date: string | number;
  amount: string | number;
  wht_amount: string | number;
  net_payable?: string | number;
  status: string | number;
  description: string | number;
};

const moduleKey = "finance.invoices";
const basePath = "/finance/invoices";

const statusColor = (s: string): "default" | "info" | "warning" | "success" | "error" => {
  if (s === "draft") return "default";
  if (s === "submitted") return "info";
  if (s === "approved") return "warning";
  if (s === "paid") return "success";
  if (s === "rejected") return "error";
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

export default function Page() {
  const { canAdd, canChange, canDelete } = usePermissions();
  const crud = useCrudList<Row>("/finance/invoices/", "AP Invoice", basePath);

  const kpis = useMemo(() => {
    const rows = crud.rows;
    const open = rows.filter((r) => !["paid", "rejected"].includes(String(r.status)));
    const today = new Date().toISOString().slice(0, 10);
    const overdue = open.filter(
      (r) => r.due_date && String(r.due_date) < today
    );
    const netOpen = open.reduce(
      (acc, r) =>
        acc +
        (Number(r.net_payable) ||
          Number(r.amount || 0) - Number(r.wht_amount || 0)),
      0
    );
    const wht = rows.reduce((acc, r) => acc + (Number(r.wht_amount) || 0), 0);
    return {
      count: rows.length,
      open: open.length,
      overdue: overdue.length,
      netOpen,
      wht,
    };
  }, [crud.rows]);

  return (
    <ModuleGate module={moduleKey}>
      <Box>
        <PageHeader
          title="Bills you owe"
          subtitle="Supplier bills, the tax held back, and what you still have to pay."
          moduleKey={moduleKey}
        />
        {!crud.loading && crud.rows.length > 0 ? (
          <Stack direction="row" spacing={1.5} flexWrap="wrap" useFlexGap sx={{ mb: 2 }}>
            <Kpi label="Bills" value={String(kpis.count)} />
            <Kpi label="Open" value={String(kpis.open)} />
            <Kpi label="Overdue" value={String(kpis.overdue)} />
            <Kpi label="Net open AP" value={formatMoney(kpis.netOpen)} />
            <Kpi label="WHT (all)" value={formatMoney(kpis.wht)} />
          </Stack>
        ) : null}
        <CrudTable
          title="Bills"
          subtitle="Record a bill, send it for approval, then mark it paid."
          rows={crud.rows}
          loading={crud.loading}
          selectedIds={crud.selectedIds}
          onToggleAll={crud.toggleAll}
          onToggleOne={crud.toggleOne}
          onRefresh={crud.load}
          onCreate={crud.openCreate}
          onEdit={(r) => {
            const st = String(r.status);
            if (st === "paid" || st === "submitted" || st === "approved") {
              crud.openView(r);
              return;
            }
            crud.openEdit(r);
          }}
          onView={crud.openView}
          onDeleteOne={crud.askDeleteOne}
          onBulkDelete={crud.askBulkDelete}
          createLabel="Record a bill"
          canCreate={canAdd(moduleKey)}
          canEdit={canChange(moduleKey)}
          canDelete={canDelete(moduleKey)}
          emptyTitle="No invoices yet"
          emptyHint="Add a vendor invoice to start AP and WHT tracking."
          columns={[
            {
              key: "invoice_no",
              header: "Vendor invoice no.",
              render: (r) => r.invoice_no ?? "—",
            },
            { key: "vendor_name", header: "Vendor", render: (r) => r.vendor_name ?? "—" },
            {
              key: "due_date",
              header: "Due",
              render: (r) => formatDate(String(r.due_date || "")),
            },
            { key: "amount", header: "Gross", render: (r) => formatMoney(r.amount) },
            { key: "wht_amount", header: "WHT", render: (r) => formatMoney(r.wht_amount) },
            {
              key: "net",
              header: "Net payable",
              render: (r) =>
                formatMoney(
                  r.net_payable ??
                    Number(r.amount || 0) - Number(r.wht_amount || 0)
                ),
            },
            {
              key: "status",
              header: "Status / LoA",
              render: (r) => (
                <Stack spacing={0.5}>
                  <Chip
                    size="small"
                    color={statusColor(String(r.status))}
                    label={humanizeStatus(String(r.status))}
                    variant="outlined"
                  />
                  <WorkflowActions
                    resourcePath="/finance/invoices/"
                    id={r.id}
                    status={String(r.status)}
                    moduleKey={moduleKey}
                    onDone={crud.load}
                  />
                </Stack>
              ),
            },
          ]}
        />
        <ConfirmDialog
          open={!!crud.confirm}
          title="Confirm delete?"
          message="This cannot be undone."
          confirmLabel="Delete"
          loading={crud.saving}
          onClose={() => crud.setConfirm(null)}
          onConfirm={crud.runConfirmDelete}
        />
      </Box>
    </ModuleGate>
  );
}
