"use client";

import { Button, Chip } from "@mui/material";
import CrudTable from "@/components/crud/CrudTable";
import ConfirmDialog from "@/components/crud/ConfirmDialog";
import ModuleGate from "@/components/ModuleGate";
import { useCrudList } from "@/hooks/useCrudList";
import { usePermissions } from "@/hooks/usePermissions";
import api from "@/lib/api";

type Role = {
  id: number;
  name: string;
  code: string;
  description: string;
  permissions: Record<string, string[]>;
  is_system: boolean;
  member_count: number;
};

const moduleKey = "settings.roles";
const basePath = "/settings/roles";

export default function RolesPage() {
  const { canAdd, canChange, canDelete } = usePermissions();
  const crud = useCrudList<Role>("/settings/roles/", "Role", basePath);

  return (
    <ModuleGate module={moduleKey}>
      <CrudTable
        title="Roles & permissions (SoD)"
        subtitle="Permissions and segregation of duties"
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
        createLabel="Add role"
        canCreate={canAdd(moduleKey)}
        canEdit={canChange(moduleKey)}
        canDelete={canDelete(moduleKey)}
        columns={[
          { key: "name", header: "Role", render: (r) => r.name },
          { key: "code", header: "Code", render: (r) => r.code },
          {
            key: "system",
            header: "Type",
            render: (r) => (
              <Chip size="small" label={r.is_system ? "System" : "Custom"} variant="outlined" />
            ),
          },
          { key: "members", header: "Members", render: (r) => r.member_count },
          {
            key: "mods",
            header: "Modules",
            render: (r) => Object.keys(r.permissions || {}).length,
          },
        ]}
      />

      <Button
        variant="outlined"
        sx={{ mt: 1 }}
        onClick={async () => {
          await api.post("/settings/roles/ensure/");
          crud.load();
        }}
      >
        Ensure default roles
      </Button>

      <ConfirmDialog
        open={!!crud.confirm}
        title={crud.confirm?.type === "bulk" ? "Delete selected roles?" : "Delete role?"}
        message={
          crud.confirm?.type === "bulk"
            ? `Permanently delete ${crud.selectedIds.length} role(s)? System roles cannot be deleted.`
            : `Delete role “${crud.confirm?.row?.name || ""}”?`
        }
        confirmLabel="Delete"
        loading={crud.saving}
        onClose={() => crud.setConfirm(null)}
        onConfirm={crud.runConfirmDelete}
      />
    </ModuleGate>
  );
}
