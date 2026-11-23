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
  code: string;
  name: string;
  customer_name?: string;
  currency?: string;
  valid_from?: string;
  valid_until?: string;
  is_active: boolean;
};

const moduleKey = "sales.pricing";
const basePath = "/sales/pricing";
const apiPath = "/sales/pricing/";

export default function PriceListPage() {
  const { canAdd, canChange, canDelete } = usePermissions();
  const crud = useCrudList<Row>(apiPath, "Price list", basePath);

  return (
    <ModuleGate module={moduleKey}>
      <>
        <CrudTable
          title="Price lists"
          subtitle="Customer / general item pricing"
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
          createLabel="New price list"
          canCreate={canAdd(moduleKey)}
          canEdit={canChange(moduleKey)}
          canDelete={canDelete(moduleKey)}
          emptyTitle="No price lists"
          emptyHint="Define unit prices by item with optional customer and validity."
          columns={[
            { key: "code", header: "Code", render: (r) => r.code },
            { key: "name", header: "Name", render: (r) => r.name },
            { key: "customer_name", header: "Customer", render: (r) => r.customer_name || "All" },
            { key: "currency", header: "CCY", render: (r) => r.currency || "—" },
            {
              key: "valid_from",
              header: "From",
              render: (r) => (r.valid_from ? formatDate(r.valid_from) : "—"),
            },
            {
              key: "is_active",
              header: "Active",
              render: (r) => (
                <Chip size="small" label={r.is_active ? "yes" : "no"} variant="outlined" />
              ),
            },
          ]}
        />
        <ConfirmDialog
          open={!!crud.confirm}
          title="Delete price list?"
          message={`Delete “${crud.confirm?.row?.code ?? ""}”?`}
          confirmLabel="Delete"
          loading={crud.saving}
          onClose={() => crud.setConfirm(null)}
          onConfirm={crud.runConfirmDelete}
        />
      </>
    </ModuleGate>
  );
}
