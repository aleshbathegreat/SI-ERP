"use client";

import { useMemo, useState } from "react";
import { Box, Chip, ToggleButton, ToggleButtonGroup } from "@mui/material";
import CrudTable from "@/components/crud/CrudTable";
import ConfirmDialog from "@/components/crud/ConfirmDialog";
import ModuleGate from "@/components/ModuleGate";
import { useCrudList } from "@/hooks/useCrudList";
import { usePermissions } from "@/hooks/usePermissions";
import { formatDate, formatMoney } from "@/lib/format";

type Row = {
  id: number;
  pr_no: string;
  preferred_vendor_name?: string;
  request_date: string;
  estimated_amount: number | string;
  currency?: string;
  status: string;
  po_no?: string;
};

const moduleKey = "procurement.requisitions";
const basePath = "/procurement/requisitions";
const apiPath = "/procurement/requisitions/";

export default function Page() {
  const { canAdd, canChange, canDelete } = usePermissions();
  const crud = useCrudList<Row>(apiPath, "Purchase requisition", basePath);
  const [statusFilter, setStatusFilter] = useState("all");

  const filtered = useMemo(() => {
    if (statusFilter === "all") return crud.rows;
    return crud.rows.filter((r) => r.status === statusFilter);
  }, [crud.rows, statusFilter]);

  return (
    <ModuleGate module={moduleKey}>
      <Box>
        <ToggleButtonGroup
          exclusive
          size="small"
          value={statusFilter}
          onChange={(_, v) => v && setStatusFilter(v)}
          sx={{ mb: 2, flexWrap: "wrap" }}
        >
          {["all", "draft", "submitted", "approved", "converted", "cancelled"].map((v) => (
            <ToggleButton key={v} value={v}>
              {v === "all" ? "All" : v}
            </ToggleButton>
          ))}
        </ToggleButtonGroup>
        <CrudTable
          title="Purchase requisitions"
          subtitle="Demand → LoA → convert to PO"
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
          createLabel="New requisition"
          canCreate={canAdd(moduleKey)}
          canEdit={canChange(moduleKey)}
          canDelete={canDelete(moduleKey)}
          emptyTitle="No requisitions"
          emptyHint="Raise a PR, submit for approval, then convert to a purchase order."
          columns={[
            { key: "pr_no", header: "PR", render: (r) => r.pr_no },
            {
              key: "preferred_vendor_name",
              header: "Vendor",
              render: (r) => r.preferred_vendor_name || "—",
            },
            {
              key: "request_date",
              header: "Date",
              render: (r) => formatDate(r.request_date),
            },
            {
              key: "estimated_amount",
              header: "Est.",
              render: (r) => formatMoney(r.estimated_amount, r.currency || "PKR"),
            },
            {
              key: "status",
              header: "Status",
              render: (r) => <Chip size="small" label={r.status} variant="outlined" />,
            },
            { key: "po_no", header: "PO", render: (r) => r.po_no || "—" },
          ]}
        />
        <ConfirmDialog
          open={!!crud.confirm}
          title={
            crud.confirm?.type === "bulk"
              ? "Delete selected requisitions?"
              : "Delete purchase requisition?"
          }
          message={
            crud.confirm?.type === "bulk"
              ? `Permanently delete ${crud.selectedIds.length} requisition(s)?`
              : `Delete “${crud.confirm?.row?.pr_no ?? ""}”?`
          }
          confirmLabel="Delete"
          loading={crud.saving}
          onClose={() => crud.setConfirm(null)}
          onConfirm={crud.runConfirmDelete}
        />
      </Box>
    </ModuleGate>
  );
}
