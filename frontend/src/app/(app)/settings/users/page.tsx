"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Chip } from "@mui/material";
import CrudTable from "@/components/crud/CrudTable";
import ModuleGate from "@/components/ModuleGate";
import { usePermissions } from "@/hooks/usePermissions";
import { listResource } from "@/lib/crudApi";
import { useSnackbar } from "notistack";

type TenantUser = {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  is_active: boolean;
  role_ids: number[];
  role_names: string[];
  profile?: { role: string; designation?: string; primary_role_name?: string };
};

const moduleKey = "settings.users";
const basePath = "/settings/users";

export default function UsersPage() {
  const { canAdd, canChange } = usePermissions();
  const { enqueueSnackbar } = useSnackbar();
  const router = useRouter();
  const [rows, setRows] = useState<TenantUser[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const users = await listResource<TenantUser>("/settings/users/");
      setRows(users);
    } catch {
      enqueueSnackbar("Failed to load users", { variant: "error" });
    } finally {
      setLoading(false);
    }
  }, [enqueueSnackbar]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <ModuleGate module={moduleKey}>
      <CrudTable
        title="Tenant users"
        subtitle="Invite members and assign roles within this organization"
        rows={rows}
        loading={loading}
        selectedIds={[]}
        onToggleAll={() => undefined}
        onToggleOne={() => undefined}
        onRefresh={load}
        onCreate={() => router.push(`${basePath}/new`)}
        onEdit={(row) => router.push(`${basePath}/${row.id}/edit`)}
        onView={(row) => router.push(`${basePath}/${row.id}`)}
        onDeleteOne={() => undefined}
        onBulkDelete={() => undefined}
        createLabel="Invite user"
        canCreate={canAdd(moduleKey)}
        canEdit={canChange(moduleKey)}
        canDelete={false}
        columns={[
          { key: "user", header: "Username", render: (r) => r.username },
          {
            key: "name",
            header: "Name",
            render: (r) => `${r.first_name || ""} ${r.last_name || ""}`.trim() || "—",
          },
          { key: "email", header: "Email", render: (r) => r.email || "—" },
          {
            key: "roles",
            header: "Roles",
            render: (r) => (r.role_names || []).join(", ") || r.profile?.role || "—",
          },
          {
            key: "status",
            header: "Status",
            render: (r) => (
              <Chip
                size="small"
                color={r.is_active ? "success" : "default"}
                label={r.is_active ? "Active" : "Inactive"}
                variant="outlined"
              />
            ),
          },
        ]}
      />
    </ModuleGate>
  );
}
