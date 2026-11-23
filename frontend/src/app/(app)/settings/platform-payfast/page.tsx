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
import PageHeader from "@/components/PageHeader";
import PlatformGate from "@/components/PlatformGate";
import api from "@/lib/api";
import { useSnackbar } from "notistack";
import { useAppSelector } from "@/store/hooks";

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

export default function PlatformPayFastPage() {
  const user = useAppSelector((s) => s.auth.user);
  const { enqueueSnackbar } = useSnackbar();
  const [form, setForm] = useState<Form>(empty);
  const [saving, setSaving] = useState(false);
  const [forbidden, setForbidden] = useState(false);

  const load = async () => {
    try {
      const { data } = await api.get("/platform/payfast/");
      setForbidden(false);
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
    } catch {
      setForbidden(true);
    }
  };

  useEffect(() => {
    load();
  }, []);

  if (forbidden) {
    return (
      <PlatformGate capability="payfast">
        <Stack spacing={2}>
          <PageHeader
            title="Platform PayFast"
            subtitle="Premier PayFast for SaaS subscription billing"
          />
          <Alert severity="warning">
            Only the platform owner can manage PayFast.
            {user?.username ? ` Signed in as ${user.username}.` : ""}
          </Alert>
        </Stack>
      </PlatformGate>
    );
  }

  return (
    <PlatformGate capability="payfast">
    <Stack spacing={2}>
      <PageHeader
        title="Platform PayFast"
        subtitle="Sandbox (ipguat) or live Premier PayFast credentials for tenant subscription payments"
      />
      <Card>
        <CardContent>
          <Alert severity={form.ready ? "success" : "info"} sx={{ mb: 2 }}>
            {form.ready
              ? `Gateway ready · ${form.environment}`
              : "Enter merchant id + secured key for the selected environment. Leave secret fields blank to keep existing values."}
          </Alert>
          <Stack spacing={1.5} maxWidth={560}>
            <TextField
              select
              label="Environment"
              value={form.environment}
              onChange={(e) => setForm({ ...form, environment: e.target.value })}
            >
              <MenuItem value="sandbox">Sandbox (UAT)</MenuItem>
              <MenuItem value="live">Live</MenuItem>
            </TextField>
            <TextField
              label="Sandbox API base"
              value={form.sandbox_api_base}
              onChange={(e) => setForm({ ...form, sandbox_api_base: e.target.value })}
            />
            <TextField
              label="Sandbox merchant ID"
              value={form.sandbox_merchant_id}
              onChange={(e) => setForm({ ...form, sandbox_merchant_id: e.target.value })}
            />
            <TextField
              label="Sandbox secured key"
              type="password"
              value={form.sandbox_secured_key}
              onChange={(e) => setForm({ ...form, sandbox_secured_key: e.target.value })}
              helperText={form.sandbox_secured_key_set ? "Set — leave blank to keep" : ""}
            />
            <TextField
              label="Sandbox hash key (optional)"
              type="password"
              value={form.sandbox_hash_key}
              onChange={(e) => setForm({ ...form, sandbox_hash_key: e.target.value })}
            />
            <TextField
              label="Live API base"
              value={form.live_api_base}
              onChange={(e) => setForm({ ...form, live_api_base: e.target.value })}
            />
            <TextField
              label="Live merchant ID"
              value={form.live_merchant_id}
              onChange={(e) => setForm({ ...form, live_merchant_id: e.target.value })}
            />
            <TextField
              label="Live secured key"
              type="password"
              value={form.live_secured_key}
              onChange={(e) => setForm({ ...form, live_secured_key: e.target.value })}
              helperText={form.live_secured_key_set ? "Set — leave blank to keep" : ""}
            />
            <TextField
              label="Live hash key (optional)"
              type="password"
              value={form.live_hash_key}
              onChange={(e) => setForm({ ...form, live_hash_key: e.target.value })}
            />
            <Button
              variant="contained"
              disabled={saving}
              onClick={async () => {
                setSaving(true);
                try {
                  const payload: Record<string, string> = { ...form };
                  delete payload.ready;
                  delete payload.sandbox_secured_key_set;
                  delete payload.live_secured_key_set;
                  for (const k of [
                    "sandbox_secured_key",
                    "sandbox_hash_key",
                    "live_secured_key",
                    "live_hash_key",
                  ]) {
                    if (!payload[k]) delete payload[k];
                  }
                  await api.put("/platform/payfast/", payload);
                  enqueueSnackbar("Platform PayFast saved", { variant: "success" });
                  load();
                } catch {
                  enqueueSnackbar("Save failed", { variant: "error" });
                } finally {
                  setSaving(false);
                }
              }}
            >
              Save PayFast
            </Button>
          </Stack>
        </CardContent>
      </Card>
    </Stack>
    </PlatformGate>
  );
}
