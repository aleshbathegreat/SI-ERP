"use client";

import { useMemo, useState } from "react";
import {
  Box,
  Chip,
  Stack,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from "@mui/material";
import CrudTable from "@/components/crud/CrudTable";
import ConfirmDialog from "@/components/crud/ConfirmDialog";
import WorkflowActions from "@/components/WorkflowActions";
import ModuleGate from "@/components/ModuleGate";
import { useCrudList } from "@/hooks/useCrudList";
import { usePermissions } from "@/hooks/usePermissions";
import { formatDate, formatMoney } from "@/lib/format";

type Row = {
  id: number;
  invoice_no: string;
  customer_name?: string;
  sales_order_no?: string;
  invoice_date: string;
  due_date?: string;
  amount: number | string;
  tax_amount?: number | string;
  status: string;
};

const moduleKey = "sales.invoices";
const basePath = "/sales/invoices";
const apiPath = "/sales/invoices/";

function Kpi({ label, value }: { label: string; value: string }) {
  return (
    <Box sx={{ flex: 1, minWidth: 100, px: 1.5, py: 1, borderBottom: "2px solid", borderColor: "divider" }}>
      <Typography variant="caption" color="text.secondary">{label}</Typography>
      <Typography variant="h6" fontWeight={700}>{value}</Typography>
    </Box>
  );
}

export default function Page() {
  const { canAdd, canChange, canDelete } = usePermissions();
  const crud = useCrudList<Row>(apiPath, "AR invoice", basePath);
  const [statusFilter, setStatusFilter] = useState("all");

  const filtered = useMemo(() => {
    if (statusFilter === "all") return crud.rows;
    return crud.rows.filter((r) => r.status === statusFilter);
  }, [crud.rows, statusFilter]);

  const kpis = useMemo(() => {
    const rows = crud.rows;
    const open = rows.filter((r) => ["submitted", "approved"].includes(r.status));
    return {
      total: rows.length,
      draft: rows.filter((r) => r.status === "draft").length,
      open: open.length,
      paid: rows.filter((r) => r.status === "paid").length,
      openValue: open.reduce((a, r) => a + Number(r.amount || 0) + Number(r.tax_amount || 0), 0),
    };
  }, [crud.rows]);

  return (
    <ModuleGate module={moduleKey}>
      <Box>
        {!crud.loading && crud.rows.length > 0 ? (
          <Stack direction="row" flexWrap="wrap" useFlexGap sx={{ mb: 2 }}>
            <Kpi label="Invoices" value={String(kpis.total)} />
            <Kpi label="Draft" value={String(kpis.draft)} />
            <Kpi label="Open" value={String(kpis.open)} />
            <Kpi label="Paid" value={String(kpis.paid)} />
            <Kpi label="Open AR" value={formatMoney(kpis.openValue)} />
          </Stack>
        ) : null}
        <ToggleButtonGroup exclusive size="small" value={statusFilter} onChange={(_, v) => v && setStatusFilter(v)} sx={{ mb: 2, flexWrap: "wrap" }}>
          {["all", "draft", "submitted", "approved", "paid", "rejected"].map((v) => (
            <ToggleButton key={v} value={v}>{v === "all" ? "All" : v}</ToggleButton>
          ))}
        </ToggleButtonGroup>
        <CrudTable
          title="AR invoices"
          subtitle="Order-to-cash · invoice → LoA → receipt"
          rows={filtered}
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
          createLabel="New AR invoice"
          canCreate={canAdd(moduleKey)}
          canEdit={canChange(moduleKey)}
          canDelete={canDelete(moduleKey)}
          emptyTitle="No AR invoices"
          emptyHint="Create from a sales order or add a customer invoice."
          columns={[
            { key: "invoice_no", header: "Invoice", render: (r) => r.invoice_no || "—" },
            { key: "customer_name", header: "Customer", render: (r) => r.customer_name || "—" },
            { key: "sales_order_no", header: "SO", render: (r) => r.sales_order_no || "—" },
            { key: "invoice_date", header: "Date", render: (r) => formatDate(r.invoice_date) },
            {
              key: "amount",
              header: "Amount",
              render: (r) => formatMoney(Number(r.amount || 0) + Number(r.tax_amount || 0)),
            },
            {
              key: "status",
              header: "Status",
              render: (r) => <Chip size="small" label={r.status} variant="outlined" />,
            },
            {
              key: "actions",
              header: "",
              render: (r) => (
                <WorkflowActions
                  resourcePath={apiPath}
                  id={r.id}
                  status={r.status}
                  moduleKey={moduleKey}
                  onDone={crud.load}
                />
              ),
            },
          ]}
        />
        <ConfirmDialog
          open={!!crud.confirm}
          title="Delete AR invoice?"
          message="Only draft/rejected invoices can be deleted."
          confirmLabel="Delete"
          loading={crud.saving}
          onClose={() => crud.setConfirm(null)}
          onConfirm={crud.runConfirmDelete}
        />
      </Box>
    </ModuleGate>
  );
}
