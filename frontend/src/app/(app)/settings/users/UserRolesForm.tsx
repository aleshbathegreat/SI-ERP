"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  Button,
  Checkbox,
  FormControlLabel,
  MenuItem,
  Stack,
  TextField,
} from "@mui/material";
import EditIcon from "@mui/icons-material/Edit";
import { useSnackbar } from "notistack";
import FormPageShell from "@/components/crud/FormPageShell";
import ModuleGate from "@/components/ModuleGate";
import { usePermissions } from "@/hooks/usePermissions";
import { type FormMode } from "@/hooks/useEntityForm";
import api from "@/lib/api";
import { getResource, listResource } from "@/lib/crudApi";

type Role = { id: number; name: string; code: string };
type TenantUser = {
  id: number;
  username: string;
  is_active: boolean;
  role_ids: number[];
};

const moduleKey = "settings.users";
const basePath = "/settings/users";

export default function UserRolesForm({ mode }: { mode: FormMode }) {
  const params = useParams();
  const id = String(params.id);
  const router = useRouter();
  const { canChange } = usePermissions();
  const { enqueueSnackbar } = useSnackbar();
  const [roles, setRoles] = useState<Role[]>([]);
  const [user, setUser] = useState<TenantUser | null>(null);
  const [assignIds, setAssignIds] = useState<number[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const readOnly = mode === "view" || !canChange(moduleKey);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      getResource<TenantUser>("/settings/users/", id),
      listResource<Role>("/settings/roles/"),
    ])
      .then(([u, roleRows]) => {
        setUser(u);
        setAssignIds(u.role_ids || []);
        setRoles(roleRows);
      })
      .catch(() => {
        enqueueSnackbar("Failed to load user", { variant: "error" });
        router.replace(basePath);
      })
      .finally(() => setLoading(false));
  }, [id, enqueueSnackbar, router]);

  const save = async () => {
    if (readOnly || !user) {
      router.push(basePath);
      return;
    }
    setSaving(true);
    try {
      await api.post(`/settings/users/${user.id}/assign-roles/`, {
        role_ids: assignIds,
      });
      enqueueSnackbar("Roles updated", { variant: "success" });
      router.push(basePath);
    } catch {
      enqueueSnackbar("Could not update roles", { variant: "error" });
    } finally {
      setSaving(false);
    }
  };

  return (
    <ModuleGate module={moduleKey}>
      <FormPageShell
        title={`Manage roles · ${user?.username || ""}`}
        backHref={basePath}
        mode={readOnly ? "view" : "edit"}
        loading={loading}
        saving={saving}
        onSubmit={save}
        extraActions={
          mode === "view" && canChange(moduleKey) ? (
            <Button
              component={Link}
              href={`${basePath}/${id}/edit`}
              variant="contained"
              startIcon={<EditIcon />}
            >
              Edit
            </Button>
          ) : null
        }
      >
        <TextField select label="Active" value={user?.is_active ? "1" : "0"} disabled>
          <MenuItem value="1">Active</MenuItem>
          <MenuItem value="0">Inactive</MenuItem>
        </TextField>
        {canChange(moduleKey) && user ? (
          <Button
            size="small"
            variant="outlined"
            sx={{ alignSelf: "flex-start" }}
            disabled={saving}
            onClick={async () => {
              setSaving(true);
              try {
                await api.post(`/settings/users/${user.id}/set-active/`, {
                  is_active: !user.is_active,
                });
                enqueueSnackbar("Status updated", { variant: "success" });
                router.push(basePath);
              } catch (e: unknown) {
                const detail =
                  (e as { response?: { data?: { detail?: string } } })?.response?.data
                    ?.detail || "Status update failed";
                enqueueSnackbar(String(detail), { variant: "error" });
              } finally {
                setSaving(false);
              }
            }}
          >
            {user.is_active ? "Deactivate user" : "Activate user"}
          </Button>
        ) : null}
        <Stack>
          {roles.map((role) => (
            <FormControlLabel
              key={role.id}
              control={
                <Checkbox
                  disabled={readOnly}
                  checked={assignIds.includes(role.id)}
                  onChange={(e) =>
                    setAssignIds((prev) =>
                      e.target.checked
                        ? [...new Set([...prev, role.id])]
                        : prev.filter((x) => x !== role.id)
                    )
                  }
                />
              }
              label={`${role.name} (${role.code})`}
            />
          ))}
        </Stack>
      </FormPageShell>
    </ModuleGate>
  );
}
