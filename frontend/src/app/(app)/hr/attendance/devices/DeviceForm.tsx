"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  Alert,
  Button,
  MenuItem,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import EditIcon from "@mui/icons-material/Edit";
import FormPageShell from "@/components/crud/FormPageShell";
import { DetailSection } from "@/components/crud/DetailPageShell";
import ModuleGate from "@/components/ModuleGate";
import { useEntityForm, type FormMode } from "@/hooks/useEntityForm";
import { usePermissions } from "@/hooks/usePermissions";
import { useParams, useSearchParams } from "next/navigation";
import api from "@/lib/api";

type Connector = {
  key: string;
  vendor: string;
  name: string;
  modes: string[];
  entitled: boolean;
  default_port?: number | null;
};

const moduleKey = "hr.attendance_devices";
const basePath = "/hr/attendance?tab=devices";
const listPath = "/hr/attendance/devices";
const resourcePath = "/hr/attendance-devices/";

function emptyForm(connectorKey = "generic_webhook") {
  return {
    device_id: "",
    connector_key: connectorKey,
    make: "",
    model_name: "",
    location: "",
    connection_mode: "push_webhook",
    host: "",
    port: "",
    username: "",
    password: "",
    api_token: "",
    is_active: true,
    notes_hint: "",
  };
}

export default function DeviceForm({ mode }: { mode: FormMode }) {
  const params = useParams();
  const searchParams = useSearchParams();
  const presetConnector = searchParams.get("connector") || "generic_webhook";
  const id = mode === "create" ? undefined : String(params.id);
  const { canChange } = usePermissions();
  const [connectors, setConnectors] = useState<Connector[]>([]);
  const [maxDevices, setMaxDevices] = useState<number | null>(null);
  const [moduleEnabled, setModuleEnabled] = useState(true);

  useEffect(() => {
    api
      .get<{
        module_enabled: boolean;
        max_devices: number | null;
        connectors: Connector[];
      }>("/hr/attendance/connectors/")
      .then((r) => {
        setModuleEnabled(r.data.module_enabled);
        setMaxDevices(r.data.max_devices);
        setConnectors(r.data.connectors || []);
      })
      .catch(() => setConnectors([]));
  }, []);

  const entitled = useMemo(
    () => connectors.filter((c) => c.entitled),
    [connectors]
  );

  const { form, setForm, loading, saving, save, readOnly } = useEntityForm({
    resourcePath,
    entityLabel: "Attendance device",
    basePath: listPath,
    mode,
    id,
    empty: emptyForm(mode === "create" ? presetConnector : "generic_webhook"),
    mapLoaded: (row) => ({
      device_id: String(row.device_id ?? ""),
      connector_key: String(row.connector_key ?? "generic_webhook"),
      make: String(row.make ?? ""),
      model_name: String(row.model_name ?? ""),
      location: String(row.location ?? ""),
      connection_mode: String(row.connection_mode ?? "push_webhook"),
      host: String(row.host ?? ""),
      port: row.port != null ? String(row.port) : "",
      username: String(row.username ?? ""),
      password: "",
      api_token: "",
      is_active: !!row.is_active,
      notes_hint: String(row.last_sync_message ?? ""),
      webhook_secret: String(row.webhook_secret ?? ""),
    }),
    mapPayload: (f) => ({
      device_id: f.device_id,
      connector_key: f.connector_key,
      make: f.make || undefined,
      model_name: f.model_name || "",
      location: f.location || "",
      connection_mode: f.connection_mode,
      host: f.host || "",
      port: f.port ? Number(f.port) : null,
      username: f.username || "",
      password: f.password || undefined,
      api_token: f.api_token || undefined,
      is_active: !!f.is_active,
    }),
  });

  useEffect(() => {
    if (mode !== "create" || !connectors.length) return;
    const c = connectors.find((x) => x.key === presetConnector && x.entitled);
    if (!c) return;
    setForm((prev) => ({
      ...prev,
      connector_key: c.key,
      make: prev.make || c.vendor || "",
      connection_mode: c.modes?.[0] || prev.connection_mode,
      port:
        c.default_port != null && !prev.port
          ? String(c.default_port)
          : prev.port,
    }));
  }, [mode, connectors, presetConnector, setForm]);

  const selected = connectors.find((c) => c.key === form.connector_key);
  const modes = selected?.modes || ["push_webhook"];

  const title =
    mode === "create" ? "Add device" : mode === "edit" ? "Edit device" : "View device";

  return (
    <ModuleGate module={moduleKey}>
      <FormPageShell
        title={title}
        subtitle="Connect a biometric / access terminal"
        backHref={basePath}
        mode={mode}
        loading={loading}
        saving={saving}
        onSubmit={save}
        maxWidth={720}
        extraActions={
          mode === "view" && canChange(moduleKey) && id ? (
            <Button
              component={Link}
              href={`${listPath}/${id}/edit`}
              variant="contained"
              startIcon={<EditIcon />}
            >
              Edit
            </Button>
          ) : null
        }
      >
        <Stack spacing={2}>
          {!moduleEnabled ? (
            <Alert severity="warning">
              Devices module not enabled on your package
              {maxDevices != null ? ` (max ${maxDevices})` : ""}.
            </Alert>
          ) : null}

          <DetailSection title="Identity" defaultExpanded>
            <Stack spacing={2}>
              <TextField
                label="Device ID"
                required
                fullWidth
                value={form.device_id}
                disabled={readOnly}
                helperText="Unique serial / terminal ID used by the device when pushing"
                onChange={(e) => setForm({ ...form, device_id: e.target.value })}
              />
              <TextField
                select
                label="Connector"
                required
                fullWidth
                value={form.connector_key}
                disabled={readOnly}
                onChange={(e) => {
                  const key = e.target.value;
                  const c = connectors.find((x) => x.key === key);
                  setForm({
                    ...form,
                    connector_key: key,
                    make: c?.vendor || form.make,
                    connection_mode: c?.modes?.[0] || form.connection_mode,
                    port:
                      c?.default_port != null
                        ? String(c.default_port)
                        : form.port,
                  });
                }}
              >
                {(mode === "create" ? entitled : connectors).map((c) => (
                  <MenuItem key={c.key} value={c.key} disabled={!c.entitled && mode === "create"}>
                    {c.vendor} · {c.name}
                    {!c.entitled ? " (locked)" : ""}
                  </MenuItem>
                ))}
              </TextField>
              {selected ? (
                <Typography variant="caption" color="text.secondary">
                  Modes: {selected.modes.join(", ")}
                </Typography>
              ) : null}
              <TextField
                select
                label="Connection mode"
                fullWidth
                value={form.connection_mode}
                disabled={readOnly}
                onChange={(e) =>
                  setForm({ ...form, connection_mode: e.target.value })
                }
              >
                {modes.map((m) => (
                  <MenuItem key={m} value={m}>
                    {m.replace(/_/g, " ")}
                  </MenuItem>
                ))}
              </TextField>
              <TextField
                label="Location"
                fullWidth
                value={form.location}
                disabled={readOnly}
                onChange={(e) => setForm({ ...form, location: e.target.value })}
              />
              <TextField
                label="Model"
                fullWidth
                value={form.model_name}
                disabled={readOnly}
                onChange={(e) => setForm({ ...form, model_name: e.target.value })}
              />
            </Stack>
          </DetailSection>

          <DetailSection title="Connection" defaultExpanded>
            <Stack spacing={2}>
              <TextField
                label="Host / URL"
                fullWidth
                value={form.host}
                disabled={readOnly}
                onChange={(e) => setForm({ ...form, host: e.target.value })}
              />
              <TextField
                label="Port"
                type="number"
                fullWidth
                value={form.port}
                disabled={readOnly}
                onChange={(e) => setForm({ ...form, port: e.target.value })}
              />
              <TextField
                label="Username"
                fullWidth
                value={form.username}
                disabled={readOnly}
                onChange={(e) => setForm({ ...form, username: e.target.value })}
              />
              <TextField
                label="Password"
                type="password"
                fullWidth
                value={form.password}
                disabled={readOnly}
                helperText={mode === "edit" ? "Leave blank to keep current" : undefined}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
              />
              <TextField
                label="API token"
                fullWidth
                value={form.api_token}
                disabled={readOnly}
                helperText={mode === "edit" ? "Leave blank to keep current" : undefined}
                onChange={(e) => setForm({ ...form, api_token: e.target.value })}
              />
              {mode === "view" && (form as { webhook_secret?: string }).webhook_secret ? (
                <TextField
                  label="Webhook secret"
                  fullWidth
                  value={(form as { webhook_secret?: string }).webhook_secret}
                  disabled
                  helperText="Send as X-Device-Secret header on push"
                />
              ) : null}
            </Stack>
          </DetailSection>
        </Stack>
      </FormPageShell>
    </ModuleGate>
  );
}
