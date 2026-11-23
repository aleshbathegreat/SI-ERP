"use client";

import {
  Chip,
  Typography,
} from "@mui/material";
import CrudTable from "@/components/crud/CrudTable";
import ConfirmDialog from "@/components/crud/ConfirmDialog";
import PlatformGate from "@/components/PlatformGate";
import PageHeader from "@/components/PageHeader";
import { useCrudList } from "@/hooks/useCrudList";

type Pkg = {
  id: number;
  name: string;
  code: string;
  price: string | number;
  interval: string;
  summary: string;
  module_keys: string[];
  core_module_keys?: string[];
  effective_module_keys?: string[];
  module_count?: number;
  max_functional_users: number;
  max_ess_users: number;
  active: boolean;
  sort: number;
};

const basePath = "/platform/packages";

export default function PlatformPackagesPage() {
  const crud = useCrudList<Pkg>("/platform/packages/", "Package", basePath);

  return (
    <PlatformGate capability="packages">
      <PageHeader
        title="Subscription packages"
        subtitle="Assign core shell modules and product modules per plan · seats · pricing"
      />
      <CrudTable
        title="Package catalog"
        subtitle="Core modules are always on · assign Finance / HR / Payroll / Billing per package"
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
        createLabel="New package"
        emptyTitle="No packages yet"
        columns={[
          {
            key: "name",
            header: "Name",
            render: (r) => (
              <>
                <strong>{r.name}</strong>
                <Typography variant="caption" display="block" color="text.secondary">
                  {r.summary}
                </Typography>
              </>
            ),
          },
          { key: "code", header: "Code", render: (r) => r.code },
          { key: "price", header: "Price", render: (r) => r.price },
          { key: "interval", header: "Interval", render: (r) => r.interval },
          {
            key: "modules",
            header: "Modules",
            render: (r) => (
              <Chip
                size="small"
                color="primary"
                variant="outlined"
                label={`${r.module_count ?? (r.effective_module_keys || []).length ?? 0} entitled`}
              />
            ),
          },
          {
            key: "seats",
            header: "Seats",
            render: (r) => `${r.max_functional_users}F / ${r.max_ess_users} ESS`,
          },
          {
            key: "status",
            header: "Status",
            render: (r) => (
              <Chip
                size="small"
                color={r.active ? "success" : "default"}
                label={r.active ? "active" : "off"}
              />
            ),
          },
        ]}
      />

      <ConfirmDialog
        open={!!crud.confirm}
        title={
          crud.confirm?.type === "bulk" ? "Delete selected packages?" : "Delete package?"
        }
        message={
          crud.confirm?.type === "bulk"
            ? `Permanently delete ${crud.selectedIds.length} package(s)? This cannot be undone.`
            : `Delete package “${crud.confirm?.row?.name}”?`
        }
        confirmLabel="Delete"
        loading={crud.saving}
        onClose={() => crud.setConfirm(null)}
        onConfirm={crud.runConfirmDelete}
      />
    </PlatformGate>
  );
}
