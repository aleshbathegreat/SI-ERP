"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  Button,
  Checkbox,
  FormControlLabel,
  MenuItem,
  TextField,
} from "@mui/material";
import EditIcon from "@mui/icons-material/Edit";
import { useSnackbar } from "notistack";
import FormPageShell from "@/components/crud/FormPageShell";
import PlatformGate from "@/components/PlatformGate";
import { type FormMode } from "@/hooks/useEntityForm";
import api from "@/lib/api";
import { getResource } from "@/lib/crudApi";

const ROLES = ["finance", "sales", "support", "technical"];
const basePath = "/platform/staff";
const resourcePath = "/platform/staff/";

const empty = {
  username: "",
  email: "",
  password: "",
  first_name: "",
  role: "support",
  title: "",
  notes: "",
  is_active: true,
};

export default function StaffForm({ mode }: { mode: FormMode }) {
  const params = useParams();
  const id = mode === "create" ? undefined : String(params.id);
  const router = useRouter();
  const { enqueueSnackbar } = useSnackbar();
  const [form, setForm] = useState(empty);
  const [loading, setLoading] = useState(mode !== "create");
  const [saving, setSaving] = useState(false);
  const readOnly = mode === "view";

  useEffect(() => {
    if (mode === "create") {
      setForm(empty);
      setLoading(false);
      return;
    }
    if (id == null) return;
    setLoading(true);
    getResource<Record<string, unknown>>(resourcePath, id)
      .then((r) => {
        setForm({
          username: String(r.username ?? ""),
          email: String(r.email ?? ""),
          password: "",
          first_name: "",
          role: String(r.role ?? "support"),
          title: String(r.title ?? ""),
          notes: String(r.notes ?? ""),
          is_active: !!r.is_active,
        });
      })
      .catch(() => {
        enqueueSnackbar("Failed to load Staff", { variant: "error" });
        router.replace(basePath);
      })
      .finally(() => setLoading(false));
  }, [mode, id, enqueueSnackbar, router]);

  const save = async () => {
    if (mode === "view") {
      router.push(basePath);
      return;
    }
    setSaving(true);
    try {
      if (mode === "create") {
        await api.post("/platform/staff/", form);
        enqueueSnackbar("Staff member created", { variant: "success" });
      } else if (id != null) {
        await api.patch(`/platform/staff/${id}/`, {
          role: form.role,
          title: form.title,
          notes: form.notes,
          is_active: form.is_active,
        });
        enqueueSnackbar("Staff updated", { variant: "success" });
      }
      router.push(basePath);
    } catch (e: unknown) {
      const msg =
        (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        "Save failed";
      enqueueSnackbar(String(msg), { variant: "error" });
    } finally {
      setSaving(false);
    }
  };

  const title =
    mode === "create"
      ? "Add platform staff"
      : mode === "edit"
        ? "Edit staff"
        : "View staff";

  return (
    <PlatformGate capability="staff">
      <FormPageShell
        title={title}
        backHref={basePath}
        mode={mode}
        loading={loading}
        saving={saving}
        onSubmit={save}
        extraActions={
          mode === "view" && id ? (
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
        {mode === "create" ? (
          <>
            <TextField
              label="Username"
              required
              value={form.username}
              onChange={(e) => setForm({ ...form, username: e.target.value })}
            />
            <TextField
              label="Email"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
            />
            <TextField
              label="Password"
              type="password"
              required
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
            />
            <TextField
              label="First name"
              value={form.first_name}
              onChange={(e) => setForm({ ...form, first_name: e.target.value })}
            />
          </>
        ) : (
          <TextField label="Username" value={form.username} disabled />
        )}
        <TextField
          select
          label="Role"
          value={form.role}
          disabled={readOnly}
          onChange={(e) => setForm({ ...form, role: e.target.value })}
        >
          {ROLES.map((r) => (
            <MenuItem key={r} value={r}>
              {r}
            </MenuItem>
          ))}
        </TextField>
        <TextField
          label="Title"
          value={form.title}
          disabled={readOnly}
          onChange={(e) => setForm({ ...form, title: e.target.value })}
        />
        <TextField
          label="Notes"
          value={form.notes}
          disabled={readOnly}
          onChange={(e) => setForm({ ...form, notes: e.target.value })}
        />
        {mode !== "create" ? (
          <FormControlLabel
            control={
              <Checkbox
                checked={form.is_active}
                disabled={readOnly}
                onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
              />
            }
            label="Active"
          />
        ) : null}
      </FormPageShell>
    </PlatformGate>
  );
}
