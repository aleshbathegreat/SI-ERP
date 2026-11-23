"use client";

import { Chip } from "@mui/material";
import CrudTable from "@/components/crud/CrudTable";
import ConfirmDialog from "@/components/crud/ConfirmDialog";
import ModuleGate from "@/components/ModuleGate";
import { useCrudList } from "@/hooks/useCrudList";
import { usePermissions } from "@/hooks/usePermissions";
import { formatDate } from "@/lib/format";

type Row = {
  id: number;
  rfq_no: string;
  rfq_date: string;
  status: string;
  awarded_vendor_name?: string;
  po_no?: string;
};

const moduleKey = "procurement.rfq";
const basePath = "/procurement/rfqs";
const apiPath = "/procurement/rfqs/";

export default function RfqList() {
  const { canAdd, canChange, canDelete } = usePermissions();
  const crud = useCrudList<Row>(apiPath, "Vendor RFQ", basePath);

  return (
    <ModuleGate module={moduleKey}>
      <>
        <CrudTable
          title="Vendor RFQs"
          subtitle="Draft → send → award winning quote → draft PO"
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
          createLabel="New RFQ"
          canCreate={canAdd(moduleKey)}
          canEdit={canChange(moduleKey)}
          canDelete={canDelete(moduleKey)}
          emptyTitle="No RFQs"
          emptyHint="Create an RFQ, collect vendor quotes, then award to raise a PO."
          columns={[
            { key: "rfq_no", header: "RFQ", render: (r) => r.rfq_no },
            { key: "rfq_date", header: "Date", render: (r) => formatDate(r.rfq_date) },
            {
              key: "status",
              header: "Status",
              render: (r) => <Chip size="small" label={r.status} variant="outlined" />,
            },
            {
              key: "awarded_vendor_name",
              header: "Awarded",
              render: (r) => r.awarded_vendor_name || "—",
            },
            { key: "po_no", header: "PO", render: (r) => r.po_no || "—" },
          ]}
        />
        <ConfirmDialog
          open={!!crud.confirm}
          title="Delete RFQ?"
          message={`Delete “${crud.confirm?.row?.rfq_no ?? ""}”?`}
          confirmLabel="Delete"
          loading={crud.saving}
          onClose={() => crud.setConfirm(null)}
          onConfirm={crud.runConfirmDelete}
        />
      </>
    </ModuleGate>
  );
}
