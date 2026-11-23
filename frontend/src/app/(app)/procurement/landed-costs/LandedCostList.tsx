"use client";

import { Chip } from "@mui/material";
import CrudTable from "@/components/crud/CrudTable";
import ConfirmDialog from "@/components/crud/ConfirmDialog";
import ModuleGate from "@/components/ModuleGate";
import { useCrudList } from "@/hooks/useCrudList";
import { usePermissions } from "@/hooks/usePermissions";
import { formatMoney } from "@/lib/format";

type Row = {
  id: number;
  grn_no?: string;
  freight_amount?: string | number;
  duty_amount?: string | number;
  other_amount?: string | number;
  total_charges?: string;
  status: string;
};

const moduleKey = "procurement.landed_cost";
const basePath = "/procurement/landed-costs";
const apiPath = "/procurement/landed-costs/";

export default function LandedCostList() {
  const { canAdd, canChange, canDelete } = usePermissions();
  const crud = useCrudList<Row>(apiPath, "Landed cost", basePath);

  return (
    <ModuleGate module={moduleKey}>
      <>
        <CrudTable
          title="Landed costs"
          subtitle="Allocate freight / duty into GRN item unit costs"
          rows={crud.rows}
          loading={crud.loading}
          selectedIds={crud.selectedIds}
          onToggleAll={crud.toggleAll}
          onToggleOne={crud.toggleOne}
          onRefresh={crud.load}
          onCreate={crud.openCreate}
          onEdit={undefined}
          onView={crud.openView}
          onDeleteOne={crud.askDeleteOne}
          onBulkDelete={crud.askBulkDelete}
          createLabel="New landed cost"
          canCreate={canAdd(moduleKey)}
          canEdit={false}
          canDelete={canDelete(moduleKey)}
          emptyTitle="No landed costs"
          emptyHint="Link a GRN and enter freight/duty, then post to roll into unit cost."
          columns={[
            { key: "id", header: "#", render: (r) => String(r.id) },
            { key: "grn_no", header: "GRN", render: (r) => r.grn_no || "—" },
            {
              key: "total_charges",
              header: "Charges",
              render: (r) => formatMoney(r.total_charges || "0"),
            },
            {
              key: "status",
              header: "Status",
              render: (r) => <Chip size="small" label={r.status} variant="outlined" />,
            },
          ]}
        />
        <ConfirmDialog
          open={!!crud.confirm}
          title="Delete landed cost?"
          message="Delete this landed cost document?"
          confirmLabel="Delete"
          loading={crud.saving}
          onClose={() => crud.setConfirm(null)}
          onConfirm={crud.runConfirmDelete}
        />
      </>
    </ModuleGate>
  );
}
