"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Stack,
  Switch,
  TextField,
  Typography,
} from "@mui/material";
import HubOutlinedIcon from "@mui/icons-material/HubOutlined";
import ModuleGate from "@/components/ModuleGate";
import PageHeader from "@/components/PageHeader";
import GuideLink from "@/components/GuideLink";
import api from "@/lib/api";
import { errorSnackbarOpts, getApiErrorMessage } from "@/lib/apiError";
import { useSnackbar } from "notistack";

type ConfigField = { key: string; label: string; secret?: boolean };

type Connector = {
  key: string;
  name: string;
  category: string;
  recommended: boolean;
  summary: string;
  capabilities: string[];
  config_fields: ConfigField[];
  linked_module?: string | null;
  docs_hint?: string;
  connection?: {
    id: number;
    status: string;
    is_enabled: boolean;
    last_test_ok: boolean | null;
  } | null;
};

type Connection = {
  id: number;
  connector_key: string;
  display_name: string;
  status: string;
  is_enabled: boolean;
  config: Record<string, string>;
  secrets_set: string[];
  last_test_ok: boolean | null;
  last_test_message: string;
  last_error: string;
  notes: string;
};

const LINK: Record<string, string> = {
  "settings.email": "/settings/email",
  "hr.attendance": "/hr/attendance?tab=devices",
  "payroll.payslips": "/payroll",
  "crm.activities": "/crm/calendar",
};

export default function IntegrationsPage() {
  const { enqueueSnackbar } = useSnackbar();
  const [connectors, setConnectors] = useState<Connector[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [conn, setConn] = useState<Connection | null>(null);
  const [config, setConfig] = useState<Record<string, string>>({});
  const [secrets, setSecrets] = useState<Record<string, string>>({});

  const load = useCallback(async () => {
    setLoading(true);
    try {
      await api.post("/settings/integrations/ensure-defaults/").catch(() => null);
      const { data } = await api.get<{ connectors: Connector[] }>(
        "/settings/integrations/catalog/"
      );
      setConnectors(data.connectors || []);
    } catch (e: unknown) {
      enqueueSnackbar(getApiErrorMessage(e, "Could not load integrations"), errorSnackbarOpts);
    } finally {
      setLoading(false);
    }
  }, [enqueueSnackbar]);

  useEffect(() => {
    load();
  }, [load]);

  const open = async (key: string) => {
    setSelected(key);
    setSecrets({});
    const c = connectors.find((x) => x.key === key);
    const id = c?.connection?.id;
    if (!id) {
      setConn(null);
      setConfig({});
      return;
    }
    try {
      const { data } = await api.get<Connection>(`/settings/integrations/connections/${id}/`);
      setConn(data);
      setConfig({ ...(data.config || {}) });
    } catch (e: unknown) {
      enqueueSnackbar(getApiErrorMessage(e, "Could not open connector"), errorSnackbarOpts);
    }
  };

  const save = async () => {
    if (!selected) return;
    setBusy("save");
    try {
      const payload: Record<string, unknown> = {
        connector_key: selected,
        config,
        is_enabled: conn?.is_enabled ?? false,
        secrets_input: Object.fromEntries(
          Object.entries(secrets).filter(([, v]) => v.trim() !== "")
        ),
      };
      const { data } = await api.post<Connection>(
        "/settings/integrations/connections/",
        payload
      );
      setConn(data);
      enqueueSnackbar("Integration saved", { variant: "success" });
      await load();
    } catch (e: unknown) {
      enqueueSnackbar(getApiErrorMessage(e, "Save failed"), errorSnackbarOpts);
    } finally {
      setBusy(null);
    }
  };

  const toggle = async (enabled: boolean) => {
    if (!conn?.id) {
      enqueueSnackbar("Save configuration first", { variant: "warning" });
      return;
    }
    setBusy("toggle");
    try {
      const { data } = await api.patch<Connection>(
        `/settings/integrations/connections/${conn.id}/`,
        { is_enabled: enabled }
      );
      setConn(data);
      await load();
    } catch (e: unknown) {
      enqueueSnackbar(getApiErrorMessage(e, "Update failed"), errorSnackbarOpts);
    } finally {
      setBusy(null);
    }
  };

  const test = async () => {
    if (!conn?.id) {
      enqueueSnackbar("Save configuration first", { variant: "warning" });
      return;
    }
    setBusy("test");
    try {
      const { data } = await api.post<Connection>(
        `/settings/integrations/connections/${conn.id}/test/`
      );
      setConn(data);
      enqueueSnackbar(data.last_test_message || (data.last_test_ok ? "OK" : "Failed"), {
        variant: data.last_test_ok ? "success" : "error",
      });
      await load();
    } catch (e: unknown) {
      enqueueSnackbar(getApiErrorMessage(e, "Test failed"), errorSnackbarOpts);
    } finally {
      setBusy(null);
    }
  };

  const meta = useMemo(
    () => connectors.find((c) => c.key === selected) || null,
    [connectors, selected]
  );

  const calendars = connectors.filter((c) => c.category === "calendar");
  const recommended = connectors.filter((c) => c.recommended && c.category !== "calendar");
  const optional = connectors.filter((c) => !c.recommended && c.category !== "calendar");

  return (
    <ModuleGate module="settings.integrations">
      <PageHeader
        title="Enterprise Integrations"
        subtitle="Microsoft 365, calendars, biometric attendance, banking, webhooks and partner APIs"
        moduleKey="settings.integrations"
        actions={<GuideLink section="integrations" label="How to connect M365" />}
      />

      <Alert severity="info" sx={{ mb: 2 }}>
        Recommended starters: <strong>Microsoft 365 email</strong> and biometric attendance devices.
        Configure M365 Graph here; attendance devices under HR → Attendance.
      </Alert>

      {loading ? (
        <Box sx={{ display: "grid", placeItems: "center", py: 6 }}>
          <CircularProgress size={32} />
        </Box>
      ) : (
        <Box
          sx={{
            display: "grid",
            gap: 2,
            gridTemplateColumns: { xs: "1fr", lg: "1.1fr 0.9fr" },
          }}
        >
          <Stack spacing={2}>
            <Typography fontWeight={700} sx={{ display: "flex", alignItems: "center", gap: 1 }}>
              <HubOutlinedIcon fontSize="small" /> Recommended
            </Typography>
            {recommended.map((c) => (
              <ConnectorCard
                key={c.key}
                c={c}
                active={selected === c.key}
                onOpen={() => open(c.key)}
              />
            ))}
            <Typography fontWeight={700} sx={{ mt: 1 }}>
              Calendars
            </Typography>
            <Typography variant="body2" color="text.secondary">
              The SI-ERP calendar stays on. Activate Microsoft 365, Google, CalDAV, or any combination. Each active calendar receives a copy of the meeting.
            </Typography>
            {calendars.map((c) => (
              <ConnectorCard
                key={c.key}
                c={c}
                active={selected === c.key}
                onOpen={() => open(c.key)}
              />
            ))}
            <Typography fontWeight={700} sx={{ mt: 1 }}>
              Optional connectors
            </Typography>
            {optional.map((c) => (
              <ConnectorCard
                key={c.key}
                c={c}
                active={selected === c.key}
                onOpen={() => open(c.key)}
              />
            ))}
          </Stack>

          <Box
            sx={{
              p: 2.5,
              borderRadius: 2,
              border: "1px solid",
              borderColor: "divider",
              bgcolor: (t) =>
                t.palette.mode === "dark" ? "rgba(255,255,255,0.03)" : "rgba(255,255,255,0.8)",
              position: { lg: "sticky" },
              top: { lg: 88 },
              alignSelf: "start",
            }}
          >
            {!meta ? (
              <Typography color="text.secondary">
                Select a connector to configure credentials, enable, and test.
              </Typography>
            ) : (
              <Stack spacing={1.5}>
                <Typography variant="h6" fontWeight={700}>
                  {meta.name}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {meta.summary}
                </Typography>
                {meta.docs_hint ? (
                  <Typography variant="caption" color="text.secondary">
                    {meta.docs_hint}
                  </Typography>
                ) : null}
                {meta.linked_module && LINK[meta.linked_module] ? (
                  <Button
                    component={Link}
                    href={LINK[meta.linked_module]}
                    size="small"
                    variant="outlined"
                  >
                    Open linked module
                  </Button>
                ) : null}

                {meta.config_fields.map((f) =>
                  f.secret ? (
                    <TextField
                      key={f.key}
                      label={f.label}
                      type="password"
                      value={secrets[f.key] || ""}
                      onChange={(e) =>
                        setSecrets((s) => ({ ...s, [f.key]: e.target.value }))
                      }
                      helperText={
                        conn?.secrets_set?.includes(f.key)
                          ? "Secret already saved — enter to replace"
                          : undefined
                      }
                    />
                  ) : (
                    <TextField
                      key={f.key}
                      label={f.label}
                      value={config[f.key] || ""}
                      onChange={(e) =>
                        setConfig((s) => ({ ...s, [f.key]: e.target.value }))
                      }
                    />
                  )
                )}

                {!meta.config_fields.length ? (
                  <Alert severity="success" variant="outlined">
                    No extra credentials here — use the linked module or enable to mark active.
                  </Alert>
                ) : null}

                <Stack direction="row" alignItems="center" justifyContent="space-between">
                  <Typography variant="body2">Enabled for production use</Typography>
                  <Switch
                    checked={Boolean(conn?.is_enabled)}
                    onChange={(_, v) => toggle(v)}
                    disabled={busy !== null}
                  />
                </Stack>

                {conn?.last_test_message ? (
                  <Alert severity={conn.last_test_ok ? "success" : "warning"}>
                    {conn.last_test_message}
                  </Alert>
                ) : null}

                <Stack direction="row" spacing={1}>
                  <Button variant="contained" disabled={busy !== null} onClick={save}>
                    Save
                  </Button>
                  <Button variant="outlined" disabled={busy !== null || !conn?.id} onClick={test}>
                    Test
                  </Button>
                </Stack>
              </Stack>
            )}
          </Box>
        </Box>
      )}
    </ModuleGate>
  );
}

function ConnectorCard({
  c,
  active,
  onOpen,
}: {
  c: Connector;
  active: boolean;
  onOpen: () => void;
}) {
  const st = c.connection?.status || "disconnected";
  const color =
    st === "active" ? "success" : st === "error" ? "error" : st === "configured" ? "info" : "default";
  return (
    <Box
      onClick={onOpen}
      sx={{
        p: 1.75,
        borderRadius: 2,
        border: "1px solid",
        borderColor: active ? "primary.main" : "divider",
        cursor: "pointer",
        bgcolor: active ? "action.selected" : "transparent",
        "&:hover": { borderColor: "primary.main" },
      }}
    >
      <Stack direction="row" justifyContent="space-between" gap={1} alignItems="flex-start">
        <Box>
          <Typography fontWeight={700}>{c.name}</Typography>
          <Typography variant="body2" color="text.secondary">
            {c.summary}
          </Typography>
        </Box>
        <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap>
          {c.recommended ? (
            <Chip size="small" label="Recommended" color="primary" variant="outlined" />
          ) : null}
          <Chip size="small" label={st} color={color as "default"} />
        </Stack>
      </Stack>
    </Box>
  );
}
