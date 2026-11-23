"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { MenuItem, TextField } from "@mui/material";
import { useSnackbar } from "notistack";
import FormPageShell from "@/components/crud/FormPageShell";
import PlatformGate from "@/components/PlatformGate";
import api from "@/lib/api";

type Tenant = {
  id: number;
  name: string;
  code: string;
  brand_name?: string;
  email?: string;
  plan: string;
  plan_status: string;
  trial_ends?: string | null;
  subscription_ends?: string | null;
  grace_days?: number;
};

const basePath = "/platform/tenants";

export default function TenantViewPage() {
  const params = useParams();
  const id = String(params.id);
  const router = useRouter();
  const { enqueueSnackbar } = useSnackbar();
  const [row, setRow] = useState<Tenant | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(() => {
    setLoading(true);
    api
      .get<{ results: Tenant[] }>("/platform/tenants/")
      .then((r) => {
        const found = (r.data.results || []).find((t) => String(t.id) === id) || null;
        if (!found) {
          enqueueSnackbar("Tenant not found", { variant: "error" });
          router.replace(basePath);
          return;
        }
        setRow(found);
      })
      .catch(() => {
        enqueueSnackbar("Unable to load tenant", { variant: "error" });
        router.replace(basePath);
      })
      .finally(() => setLoading(false));
  }, [id, enqueueSnackbar, router]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <PlatformGate capability="tenants">
      <FormPageShell
        title={`Tenant · ${row?.brand_name || row?.name || ""}`}
        backHref={basePath}
        mode="view"
        loading={loading}
      >
        {row ? (
          <>
            <TextField label="Code" value={row.code} disabled />
            <TextField label="Email" value={row.email || ""} disabled />
            <TextField label="Plan" value={row.plan} disabled />
            <TextField label="Plan status" value={row.plan_status} disabled />
            <TextField label="Trial ends" value={row.trial_ends || "—"} disabled />
            <TextField
              label="Subscription ends"
              value={row.subscription_ends || "—"}
              disabled
            />
            <TextField
              label="Grace days"
              value={String(row.grace_days ?? 7)}
              disabled
            />
            <TextField
              select
              label="Change plan status"
              value={row.plan_status}
              onChange={async (e) => {
                try {
                  await api.patch("/platform/tenants/", {
                    id: row.id,
                    plan_status: e.target.value,
                  });
                  enqueueSnackbar("Updated", { variant: "success" });
                  load();
                } catch {
                  enqueueSnackbar("Update failed", { variant: "error" });
                }
              }}
            >
              <MenuItem value="active">active</MenuItem>
              <MenuItem value="past_due">past_due</MenuItem>
              <MenuItem value="canceled">canceled</MenuItem>
            </TextField>
          </>
        ) : null}
      </FormPageShell>
    </PlatformGate>
  );
}
