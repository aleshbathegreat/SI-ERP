"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Chip } from "@mui/material";
import CrudTable from "@/components/crud/CrudTable";
import ConfirmDialog from "@/components/crud/ConfirmDialog";
import FormDialog from "@/components/crud/FormDialog";
import RelationSelect, { RELATIONS } from "@/components/crud/RelationSelect";
import ModuleGate from "@/components/ModuleGate";
import { useCrudList } from "@/hooks/useCrudList";
import { usePermissions } from "@/hooks/usePermissions";
import { useRecordAction } from "@/hooks/useRecordAction";

type Row = {
  id: number;
  pick_no: string;
  sales_order_no?: string;
  delivery_note_no?: string;
  warehouse_code?: string;
  status: string;
};

const moduleKey = "inventory.pick_lists";
const basePath = "/inventory/pick-lists";
const apiPath = "/inventory/pick-lists/";

export default function Page() {
  const router = useRouter();
  const { canAdd, canDelete } = usePermissions();
  const crud = useCrudList<Row>(apiPath, "Pick list", basePath);
  const { run, busy } = useRecordAction();
  const [open, setOpen] = useState(false);
  const [salesOrder, setSalesOrder] = useState("");
  const [warehouse, setWarehouse] = useState("");

  const create = async () => {
    if (!salesOrder) return;
    const res = await run<{ id: number; pick_no: string }>(
      "create-pick",
      `${apiPath}create-from-order/`,
      {
        body: {
          sales_order: Number(salesOrder),
          ...(warehouse ? { warehouse: Number(warehouse) } : {}),
        },
        success: (d) => `Pick list ${d.pick_no} created`,
      }
    );
    if (res) {
      setOpen(false);
      router.push(`${basePath}/${res.id}`);
    }
  };

  return (
    <ModuleGate module={moduleKey}>
      <>
        <CrudTable
          title="Pick lists"
          subtitle="Warehouse picking from confirmed sales orders"
          rows={crud.rows}
          loading={crud.loading}
          selectedIds={crud.selectedIds}
          onToggleAll={crud.toggleAll}
          onToggleOne={crud.toggleOne}
          onRefresh={crud.load}
          onCreate={() => setOpen(true)}
          onEdit={crud.openView}
          onView={crud.openView}
          onDeleteOne={crud.askDeleteOne}
          onBulkDelete={crud.askBulkDelete}
          createLabel="Create from order"
          canCreate={canAdd(moduleKey)}
          canEdit={false}
          canDelete={canDelete(moduleKey)}
          emptyTitle="No pick lists"
          emptyHint="Create a pick list from a confirmed sales order."
          columns={[
            { key: "pick_no", header: "Pick no", render: (r) => r.pick_no },
            { key: "so", header: "Sales order", render: (r) => r.sales_order_no || "—" },
            { key: "dn", header: "Delivery note", render: (r) => r.delivery_note_no || "—" },
            { key: "wh", header: "Warehouse", render: (r) => r.warehouse_code || "—" },
            {
              key: "status",
              header: "Status",
              render: (r) => <Chip size="small" label={r.status} variant="outlined" />,
            },
          ]}
        />
        <FormDialog
          open={open}
          title="Create pick list from sales order"
          loading={busy}
          submitLabel="Create"
          onClose={() => setOpen(false)}
          onSubmit={() => void create()}
        >
          <RelationSelect
            label="Sales order"
            required
            value={salesOrder}
            onChange={setSalesOrder}
            relation={RELATIONS.salesOrder}
          />
          <RelationSelect
            label="Warehouse (optional)"
            value={warehouse}
            onChange={setWarehouse}
            relation={{ ...RELATIONS.warehouse, createFields: [] }}
          />
        </FormDialog>
        <ConfirmDialog
          open={!!crud.confirm}
          title="Delete pick list?"
          message={`Delete “${crud.confirm?.row?.pick_no ?? ""}”?`}
          confirmLabel="Delete"
          loading={crud.saving}
          onClose={() => crud.setConfirm(null)}
          onConfirm={crud.runConfirmDelete}
        />
      </>
    </ModuleGate>
  );
}
