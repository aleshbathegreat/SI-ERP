"use client";

import { Chip } from "@mui/material";
import CrudTable from "@/components/crud/CrudTable";
import ConfirmDialog from "@/components/crud/ConfirmDialog";
import ModuleGate from "@/components/ModuleGate";
import { useCrudList } from "@/hooks/useCrudList";
import { usePermissions } from "@/hooks/usePermissions";
import { formatDate, formatMoney } from "@/lib/format";

type Row = {
  id: number;
  rma_no: string;
  customer_name?: string;
  order_no?: string;
  return_date: string;
  status: string;
  total?: string;
};

const moduleKey = "sales.returns";
const basePath = "/sales/returns";
const apiPath = "/sales/returns/";

export default function SalesReturnList() {
  const { canAdd, canChange, canDelete } = usePermissions();
  const crud = useCrudList<Row>(apiPath, "Sales return", basePath);

  return (
    <ModuleGate module={moduleKey}>
      <>
        <CrudTable
          title="Sales returns (RMA)"
          subtitle="Customer returns · post credit stock receipt"
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
          createLabel="New RMA"
          canCreate={canAdd(moduleKey)}
          canEdit={canChange(moduleKey)}
          canDelete={canDelete(moduleKey)}
          emptyTitle="No returns"
          emptyHint="Create an RMA linked to a customer / SO, then post to restock."
          columns={[
            { key: "rma_no", header: "RMA", render: (r) => r.rma_no },
            { key: "customer_name", header: "Customer", render: (r) => r.customer_name || "—" },
            { key: "order_no", header: "SO", render: (r) => r.order_no || "—" },
            { key: "return_date", header: "Date", render: (r) => formatDate(r.return_date) },
            { key: "total", header: "Value", render: (r) => formatMoney(r.total || "0") },
            {
              key: "status",
              header: "Status",
              render: (r) => <Chip size="small" label={r.status} variant="outlined" />,
            },
          ]}
        />
        <ConfirmDialog
          open={!!crud.confirm}
          title="Delete return?"
          message={`Delete “${crud.confirm?.row?.rma_no ?? ""}”?`}
          confirmLabel="Delete"
          loading={crud.saving}
          onClose={() => crud.setConfirm(null)}
          onConfirm={crud.runConfirmDelete}
        />
      </>
    </ModuleGate>
  );
}
