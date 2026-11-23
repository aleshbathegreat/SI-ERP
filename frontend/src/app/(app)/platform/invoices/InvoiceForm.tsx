"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  Button,
  MenuItem,
  Stack,
  TextField,
} from "@mui/material";
import EditIcon from "@mui/icons-material/Edit";
import { useSnackbar } from "notistack";
import FormPageShell from "@/components/crud/FormPageShell";
import PlatformGate from "@/components/PlatformGate";
import { type FormMode } from "@/hooks/useEntityForm";
import api from "@/lib/api";
import { getResource, listResource, updateResource } from "@/lib/crudApi";

type TenantOpt = { id: number; name: string; code: string };

const basePath = "/platform/invoices";
const resourcePath = "/platform/invoices/";

const empty = {
  organization: "",
  plan_code: "monthly",
  amount: "7500",
  tax_amount: "0",
  description: "",
  due_days: "14",
};

export default function PlatformInvoiceForm({ mode }: { mode: FormMode }) {
  const params = useParams();
  const id = mode === "create" ? undefined : String(params.id);
  const router = useRouter();
  const { enqueueSnackbar } = useSnackbar();
  const [tenants, setTenants] = useState<TenantOpt[]>([]);
  const [form, setForm] = useState(empty);
  const [loading, setLoading] = useState(mode !== "create");
  const [saving, setSaving] = useState(false);
  const readOnly = mode === "view";

  useEffect(() => {
    listResource<TenantOpt>("/platform/tenants/")
      .then(setTenants)
      .catch(() => undefined);
  }, []);

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
          organization: String(r.organization ?? ""),
          plan_code: String(r.plan_code || "monthly"),
          amount: String(r.amount ?? "0"),
          tax_amount: String(r.tax_amount || 0),
          description: String(r.description || ""),
          due_days: "14",
        });
      })
      .catch(() => {
        enqueueSnackbar("Failed to load Invoice", { variant: "error" });
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
        await api.post("/platform/invoices/", {
          organization: Number(form.organization),
          plan_code: form.plan_code,
          amount: form.amount,
          tax_amount: form.tax_amount,
          description: form.description,
          due_days: Number(form.due_days),
          status: "sent",
        });
        enqueueSnackbar("Invoice created", { variant: "success" });
      } else if (id != null) {
        await updateResource(resourcePath, id, {
          description: form.description,
          amount: form.amount,
          tax_amount: form.tax_amount,
          plan_code: form.plan_code,
        });
        enqueueSnackbar("Invoice updated", { variant: "success" });
      }
      router.push(basePath);
    } catch {
      enqueueSnackbar("Save failed", { variant: "error" });
    } finally {
      setSaving(false);
    }
  };

  const title =
    mode === "create"
      ? "New SaaS invoice"
      : mode === "edit"
        ? "Edit invoice"
        : "View invoice";

  return (
    <PlatformGate capability="invoices">
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
        <TextField
          select
          label="Tenant"
          value={form.organization}
          disabled={readOnly || mode === "edit"}
          onChange={(e) => setForm({ ...form, organization: e.target.value })}
        >
          {tenants.map((t) => (
            <MenuItem key={t.id} value={String(t.id)}>
              {t.name} ({t.code})
            </MenuItem>
          ))}
        </TextField>
        <TextField
          select
          label="Plan"
          value={form.plan_code}
          disabled={readOnly}
          onChange={(e) => setForm({ ...form, plan_code: e.target.value })}
        >
          <MenuItem value="monthly">monthly</MenuItem>
          <MenuItem value="annual">annual</MenuItem>
          <MenuItem value="enterprise">enterprise</MenuItem>
        </TextField>
        <Stack direction="row" spacing={1}>
          <TextField
            label="Amount"
            value={form.amount}
            disabled={readOnly}
            fullWidth
            onChange={(e) => setForm({ ...form, amount: e.target.value })}
          />
          <TextField
            label="Tax"
            value={form.tax_amount}
            disabled={readOnly}
            fullWidth
            onChange={(e) => setForm({ ...form, tax_amount: e.target.value })}
          />
          {mode === "create" ? (
            <TextField
              label="Due days"
              value={form.due_days}
              fullWidth
              onChange={(e) => setForm({ ...form, due_days: e.target.value })}
            />
          ) : null}
        </Stack>
        <TextField
          label="Description"
          value={form.description}
          disabled={readOnly}
          onChange={(e) => setForm({ ...form, description: e.target.value })}
        />
      </FormPageShell>
    </PlatformGate>
  );
}
