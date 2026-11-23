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
  pret_no: string;
  vendor_name?: string;
  po_no?: string;
  return_date: string;
  status: string;
  total?: string;
};

const moduleKey = "procurement.returns";
const basePath = "/procurement/returns";
const apiPath = "/procurement/returns/";

export default function PurchaseReturnList() {
  const { canAdd, canChange, canDelete } = usePermissions();
  const crud = useCrudList<Row>(apiPath, "Purchase return", basePath);

  return (
    <ModuleGate module={moduleKey}>
      <>
        <CrudTable
          title="Purchase returns"
          subtitle="Vendor returns · issue stock out"
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
          createLabel="New return"
          canCreate={canAdd(moduleKey)}
          canEdit={canChange(moduleKey)}
          canDelete={canDelete(moduleKey)}
          emptyTitle="No purchase returns"
          emptyHint="Create a return against a vendor / PO, then post to issue stock."
          columns={[
            { key: "pret_no", header: "Return", render: (r) => r.pret_no },
            { key: "vendor_name", header: "Vendor", render: (r) => r.vendor_name || "—" },
            { key: "po_no", header: "PO", render: (r) => r.po_no || "—" },
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
          message={`Delete “${crud.confirm?.row?.pret_no ?? ""}”?`}
          confirmLabel="Delete"
          loading={crud.saving}
          onClose={() => crud.setConfirm(null)}
          onConfirm={crud.runConfirmDelete}
        />
      </>
    </ModuleGate>
  );
}
