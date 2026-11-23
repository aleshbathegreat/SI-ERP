"use client";

import { Chip } from "@mui/material";
import CrudTable from "@/components/crud/CrudTable";
import ConfirmDialog from "@/components/crud/ConfirmDialog";
import ModuleGate from "@/components/ModuleGate";
import { usePeriodActions } from "@/components/finance/usePeriodActions";
import { useCrudList } from "@/hooks/useCrudList";
import { usePermissions } from "@/hooks/usePermissions";
import { PERIOD_MONTHS, getEntityDef } from "@/lib/entityCrudDefs";

const def = getEntityDef("finance/periods")!;

type Period = {
  id: number;
  name: string;
  year: number;
  month: number;
  is_locked: boolean;
};

export default function AccountingPeriodsPage() {
  const { canAdd, canChange, canDelete } = usePermissions();
  const crud = useCrudList<Period>(def.apiPath, def.entityLabel, `/${def.route}`);
  const { rowActions } = usePeriodActions();

  return (
    <ModuleGate module={def.moduleKey}>
      <>
        <CrudTable
          title={def.listTitle}
          subtitle={def.listSubtitle}
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
          createLabel={def.createLabel}
          canCreate={canAdd(def.moduleKey)}
          canEdit={canChange(def.moduleKey)}
          canDelete={canDelete(def.moduleKey)}
          emptyTitle="No periods yet"
          emptyHint="Add a month to lock or unlock it."
          getRowActions={(row) => rowActions(row, crud.load)}
          columns={[
            { key: "name", header: "Period", render: (r) => r.name },
            { key: "year", header: "Year", render: (r) => r.year },
            {
              key: "month",
              header: "Month",
              render: (r) => PERIOD_MONTHS[r.month - 1] || r.month,
            },
            {
              key: "status",
              header: "Status",
              render: (r) => (
                <Chip
                  size="small"
                  color={r.is_locked ? "warning" : "success"}
                  label={r.is_locked ? "Locked" : "Open"}
                />
              ),
            },
          ]}
        />
        <ConfirmDialog
          open={!!crud.confirm}
          title={
            crud.confirm?.type === "bulk" ? "Delete selected periods?" : "Delete period?"
          }
          message={
            crud.confirm?.type === "bulk"
              ? `Delete ${crud.selectedIds.length} period(s)?`
              : `Delete “${crud.confirm?.row?.name ?? ""}”?`
          }
          confirmLabel="Delete"
          loading={crud.saving}
          onClose={() => crud.setConfirm(null)}
          onConfirm={crud.runConfirmDelete}
        />
      </>
    </ModuleGate>
  );
}
