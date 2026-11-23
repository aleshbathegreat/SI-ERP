"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  Box,
  Button,
  Checkbox,
  FormControlLabel,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import EditIcon from "@mui/icons-material/Edit";
import FormPageShell from "@/components/crud/FormPageShell";
import ModuleGate from "@/components/ModuleGate";
import { useEntityForm, type FormMode } from "@/hooks/useEntityForm";
import { usePermissions } from "@/hooks/usePermissions";
import api from "@/lib/api";

type ModuleItem = { key: string; label: string; actions: string[] };

const ACTIONS = ["view", "add", "change", "delete"] as const;
const moduleKey = "settings.roles";
const basePath = "/settings/roles";
const resourcePath = "/settings/roles/";

const empty = {
  name: "",
  code: "",
  description: "",
  permissions: {} as Record<string, string[]>,
  is_system: false,
};

export default function RoleForm({ mode }: { mode: FormMode }) {
  const params = useParams();
  const id = mode === "create" ? undefined : String(params.id);
  const { canChange } = usePermissions();
  const [modules, setModules] = useState<ModuleItem[]>([]);
  const { form, setForm, loading, saving, save, readOnly } = useEntityForm({
    resourcePath,
    entityLabel: "Role",
    basePath,
    mode,
    id,
    empty,
    mapLoaded: (row) => ({
      name: String(row.name ?? ""),
      code: String(row.code ?? ""),
      description: String(row.description ?? ""),
      permissions: { ...((row.permissions as Record<string, string[]>) || {}) },
      is_system: !!row.is_system,
    }),
    mapPayload: (f) => ({
      name: f.name,
      code: f.code,
      description: f.description,
      permissions: f.permissions,
    }),
  });

  useEffect(() => {
    api
      .get<ModuleItem[]>("/settings/modules/")
      .then((r) => setModules(r.data))
      .catch(() => undefined);
  }, []);

  const permsLocked = readOnly || !!form.is_system;

  const toggleAction = (mod: string, action: string, checked: boolean) => {
    setForm((prev) => {
      const current = new Set(prev.permissions[mod] || []);
      if (checked) current.add(action);
      else current.delete(action);
      const next = { ...prev.permissions };
      if (current.size) next[mod] = Array.from(current);
      else delete next[mod];
      return { ...prev, permissions: next };
    });
  };

  const grantAll = useMemo(
    () => () => {
      const permissions: Record<string, string[]> = {};
      modules.forEach((m) => {
        permissions[m.key] = [...ACTIONS];
      });
      setForm((prev) => ({ ...prev, permissions }));
    },
    [modules, setForm]
  );

  const title =
    mode === "create" ? "Add role" : mode === "edit" ? "Edit role" : "View role";

  return (
    <ModuleGate module={moduleKey}>
      <FormPageShell
        title={title}
        backHref={basePath}
        mode={mode}
        loading={loading}
        saving={saving}
        onSubmit={save}
        maxWidth={960}
        extraActions={
          mode === "view" && canChange(moduleKey) && id ? (
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
        <TextField
          label="Name"
          required
          value={form.name}
          disabled={readOnly && mode !== "edit"}
          onChange={(e) => setForm({ ...form, name: e.target.value })}
        />
        <TextField
          label="Code"
          required
          value={form.code}
          disabled={mode !== "create"}
          onChange={(e) =>
            setForm({
              ...form,
              code: e.target.value.toLowerCase().replace(/\s+/g, "-"),
            })
          }
        />
        <TextField
          label="Description"
          multiline
          minRows={2}
          value={form.description}
          disabled={mode === "view"}
          onChange={(e) => setForm({ ...form, description: e.target.value })}
        />
        {mode !== "view" && !form.is_system ? (
          <Button onClick={grantAll} size="small" sx={{ alignSelf: "flex-start" }}>
            Grant all modules
          </Button>
        ) : null}
        <Box
          sx={{
            maxHeight: 420,
            overflow: "auto",
            border: 1,
            borderColor: "divider",
            p: 1.5,
            borderRadius: 1,
          }}
        >
          {modules.map((m) => (
            <Box key={m.key} sx={{ mb: 1.5 }}>
              <Typography variant="subtitle2">{m.label}</Typography>
              <Stack direction="row" flexWrap="wrap">
                {ACTIONS.map((action) => (
                  <FormControlLabel
                    key={action}
                    control={
                      <Checkbox
                        size="small"
                        checked={(form.permissions[m.key] || []).includes(action)}
                        disabled={permsLocked}
                        onChange={(e) => toggleAction(m.key, action, e.target.checked)}
                      />
                    }
                    label={action}
                  />
                ))}
              </Stack>
            </Box>
          ))}
        </Box>
      </FormPageShell>
    </ModuleGate>
  );
}
