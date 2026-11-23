"use client";

import { useEffect, useState } from "react";
import {
  Alert,
  Button,
  Card,
  CardContent,
  MenuItem,
  Stack,
  TextField,
} from "@mui/material";
import ModuleGate from "@/components/ModuleGate";
import PageHeader from "@/components/PageHeader";
import api from "@/lib/api";
import { useSnackbar } from "notistack";
import { usePermissions } from "@/hooks/usePermissions";

type Form = {
  environment: string;
  sandbox_api_base: string;
  sandbox_merchant_id: string;
  sandbox_secured_key: string;
  sandbox_hash_key: string;
  live_api_base: string;
  live_merchant_id: string;
  live_secured_key: string;
  live_hash_key: string;
  ready?: boolean;
  sandbox_secured_key_set?: boolean;
  live_secured_key_set?: boolean;
};

const empty: Form = {
  environment: "sandbox",
  sandbox_api_base: "https://ipguat.apps.net.pk/Ecommerce/api",
  sandbox_merchant_id: "",
  sandbox_secured_key: "",
  sandbox_hash_key: "",
  live_api_base: "https://ipg1.apps.net.pk/Ecommerce/api",
  live_merchant_id: "",
  live_secured_key: "",
  live_hash_key: "",
};

export default function TenantPayGatewayPage() {
  const { canChange } = usePermissions();
  const { enqueueSnackbar } = useSnackbar();
  const [form, setForm] = useState<Form>(empty);
  const [saving, setSaving] = useState(false);

  const load = async () => {
    const { data } = await api.get("/settings/pay-gateway/");
    setForm({
      environment: data.environment || "sandbox",
      sandbox_api_base: data.sandbox_api_base || empty.sandbox_api_base,
      sandbox_merchant_id: data.sandbox_merchant_id || "",
      sandbox_secured_key: "",
      sandbox_hash_key: "",
      live_api_base: data.live_api_base || empty.live_api_base,
      live_merchant_id: data.live_merchant_id || "",
      live_secured_key: "",
      live_hash_key: "",
      ready: data.ready,
      sandbox_secured_key_set: data.sandbox_secured_key_set,
      live_secured_key_set: data.live_secured_key_set,
    });
  };

  useEffect(() => {
    load().catch(() => undefined);
  }, []);

  return (
    <ModuleGate module="billing">
      <PageHeader
        title="Tenant PayFast"
        subtitle="Optional — your own Premier PayFast for company-collected payments (not SaaS subscription billing)"
      />
      <Card>
        <CardContent>
          <Alert severity="info" sx={{ mb: 2 }}>
            SaaS plan renewals use the platform PayFast. Configure this only if your tenant
            collects its own customer payments.
            {form.ready ? " Status: ready." : ""}
          </Alert>
          <Stack spacing={1.5} maxWidth={560}>
            <TextField
              select
              label="Environment"
              value={form.environment}
              disabled={!canChange("billing")}
              onChange={(e) => setForm({ ...form, environment: e.target.value })}
            >
              <MenuItem value="sandbox">Sandbox (UAT)</MenuItem>
              <MenuItem value="live">Live</MenuItem>
            </TextField>
            <TextField
              label="Sandbox merchant ID"
              value={form.sandbox_merchant_id}
              disabled={!canChange("billing")}
              onChange={(e) => setForm({ ...form, sandbox_merchant_id: e.target.value })}
            />
            <TextField
              label="Sandbox secured key"
              type="password"
              value={form.sandbox_secured_key}
              disabled={!canChange("billing")}
              onChange={(e) => setForm({ ...form, sandbox_secured_key: e.target.value })}
            />
            <TextField
              label="Live merchant ID"
              value={form.live_merchant_id}
              disabled={!canChange("billing")}
              onChange={(e) => setForm({ ...form, live_merchant_id: e.target.value })}
            />
            <TextField
              label="Live secured key"
              type="password"
              value={form.live_secured_key}
              disabled={!canChange("billing")}
              onChange={(e) => setForm({ ...form, live_secured_key: e.target.value })}
            />
            <Button
              variant="contained"
              disabled={!canChange("billing") || saving}
              onClick={async () => {
                setSaving(true);
                try {
                  const payload: Record<string, string> = {
                    environment: form.environment,
                    sandbox_api_base: form.sandbox_api_base,
                    sandbox_merchant_id: form.sandbox_merchant_id,
                    live_api_base: form.live_api_base,
                    live_merchant_id: form.live_merchant_id,
                  };
                  if (form.sandbox_secured_key)
                    payload.sandbox_secured_key = form.sandbox_secured_key;
                  if (form.sandbox_hash_key) payload.sandbox_hash_key = form.sandbox_hash_key;
                  if (form.live_secured_key) payload.live_secured_key = form.live_secured_key;
                  if (form.live_hash_key) payload.live_hash_key = form.live_hash_key;
                  await api.put("/settings/pay-gateway/", payload);
                  enqueueSnackbar("Tenant PayFast saved", { variant: "success" });
                  load();
                } catch {
                  enqueueSnackbar("Save failed (owner only)", { variant: "error" });
                } finally {
                  setSaving(false);
                }
              }}
            >
              Save tenant gateway
            </Button>
          </Stack>
        </CardContent>
      </Card>
    </ModuleGate>
  );
}
