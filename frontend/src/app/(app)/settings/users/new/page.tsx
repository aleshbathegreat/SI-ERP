"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Checkbox, FormControlLabel, Stack, TextField } from "@mui/material";
import { useSnackbar } from "notistack";
import FormPageShell from "@/components/crud/FormPageShell";
import ModuleGate from "@/components/ModuleGate";
import api from "@/lib/api";
import { listResource } from "@/lib/crudApi";

type Role = { id: number; name: string; code: string };

const moduleKey = "settings.users";
const basePath = "/settings/users";

const emptyInvite = {
  username: "",
  password: "",
  email: "",
  first_name: "",
  last_name: "",
  phone: "",
  designation: "",
  role_ids: [] as number[],
};

export default function InviteUserPage() {
  const router = useRouter();
  const { enqueueSnackbar } = useSnackbar();
  const [roles, setRoles] = useState<Role[]>([]);
  const [invite, setInvite] = useState(emptyInvite);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    listResource<Role>("/settings/roles/")
      .then(setRoles)
      .catch(() => undefined);
  }, []);

  return (
    <ModuleGate module={moduleKey}>
      <FormPageShell
        title="Invite user"
        backHref={basePath}
        mode="create"
        saving={saving}
        onSubmit={async () => {
          setSaving(true);
          try {
            await api.post("/settings/users/invite/", invite);
            enqueueSnackbar("User invited", { variant: "success" });
            router.push(basePath);
          } catch (e: unknown) {
            const detail =
              (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
              "Invite failed";
            enqueueSnackbar(String(detail), { variant: "error" });
          } finally {
            setSaving(false);
          }
        }}
      >
        <TextField
          label="Username"
          required
          value={invite.username}
          onChange={(e) => setInvite({ ...invite, username: e.target.value })}
        />
        <TextField
          label="Password"
          required
          type="password"
          value={invite.password}
          onChange={(e) => setInvite({ ...invite, password: e.target.value })}
        />
        <TextField
          label="Email"
          value={invite.email}
          onChange={(e) => setInvite({ ...invite, email: e.target.value })}
        />
        <TextField
          label="First name"
          value={invite.first_name}
          onChange={(e) => setInvite({ ...invite, first_name: e.target.value })}
        />
        <TextField
          label="Last name"
          value={invite.last_name}
          onChange={(e) => setInvite({ ...invite, last_name: e.target.value })}
        />
        <TextField
          label="Designation"
          value={invite.designation}
          onChange={(e) => setInvite({ ...invite, designation: e.target.value })}
        />
        <Stack>
          {roles.map((role) => (
            <FormControlLabel
              key={role.id}
              control={
                <Checkbox
                  checked={invite.role_ids.includes(role.id)}
                  onChange={(e) =>
                    setInvite((prev) => ({
                      ...prev,
                      role_ids: e.target.checked
                        ? [...new Set([...prev.role_ids, role.id])]
                        : prev.role_ids.filter((x) => x !== role.id),
                    }))
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
