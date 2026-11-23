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
  st_no: string;
  warehouse_name?: string;
  count_date: string;
  status: string;
};

const moduleKey = "inventory.stocktake";
const basePath = "/inventory/stocktakes";
const apiPath = "/inventory/stocktakes/";

export default function StocktakeList() {
  const { canAdd, canChange, canDelete } = usePermissions();
  const crud = useCrudList<Row>(apiPath, "Stocktake", basePath);

  return (
    <ModuleGate module={moduleKey}>
      <>
        <CrudTable
          title="Stocktakes"
          subtitle="Physical count vs system qty · post variance movements"
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
          createLabel="New stocktake"
          canCreate={canAdd(moduleKey)}
          canEdit={canChange(moduleKey)}
          canDelete={canDelete(moduleKey)}
          emptyTitle="No stocktakes"
          emptyHint="Count warehouse stock and post adjustments for variances."
          columns={[
            { key: "st_no", header: "Doc", render: (r) => r.st_no },
            { key: "warehouse_name", header: "Warehouse", render: (r) => r.warehouse_name || "—" },
            { key: "count_date", header: "Date", render: (r) => formatDate(r.count_date) },
            {
              key: "status",
              header: "Status",
              render: (r) => <Chip size="small" label={r.status} variant="outlined" />,
            },
          ]}
        />
        <ConfirmDialog
          open={!!crud.confirm}
          title="Delete stocktake?"
          message={`Delete “${crud.confirm?.row?.st_no ?? ""}”?`}
          confirmLabel="Delete"
          loading={crud.saving}
          onClose={() => crud.setConfirm(null)}
          onConfirm={crud.runConfirmDelete}
        />
      </>
    </ModuleGate>
  );
}
