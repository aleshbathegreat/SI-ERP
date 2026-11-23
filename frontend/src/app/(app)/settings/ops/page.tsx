"use client";

import { useEffect, useState } from "react";
import { Alert, Button, Card, CardContent, Stack, Typography } from "@mui/material";
import PageHeader from "@/components/PageHeader";
import ModuleGate from "@/components/ModuleGate";
import api from "@/lib/api";
import { useSnackbar } from "notistack";

export default function OpsPage() {
  const { enqueueSnackbar } = useSnackbar();
  const [status, setStatus] = useState<Record<string, unknown> | null>(null);
  const [health, setHealth] = useState<Record<string, unknown> | null>(null);

  const refresh = async () => {
    const [h, s] = await Promise.all([
      api.get("/health/"),
      api.get("/ops/status/"),
    ]);
    setHealth(h.data);
    setStatus(s.data);
  };

  useEffect(() => {
    refresh().catch(() => undefined);
  }, []);

  return (
    <ModuleGate module="settings.roles">
      <PageHeader
        title="Operations"
        subtitle="Health, SMTP verification and database backup"
        moduleKey="settings.roles"
      />
      <Stack spacing={2}>
        <Card>
          <CardContent>
            <Typography variant="h6">Health</Typography>
            <Typography variant="body2">
              {health ? JSON.stringify(health) : "Loading…"}
            </Typography>
          </CardContent>
        </Card>
        <Card>
          <CardContent>
            <Typography variant="h6">Runtime</Typography>
            <Typography variant="body2" component="pre" sx={{ whiteSpace: "pre-wrap" }}>
              {status ? JSON.stringify(status, null, 2) : "Loading…"}
            </Typography>
            {!status?.debug ? null : (
              <Alert severity="warning" sx={{ mt: 1 }}>
                DEBUG is on — disable for production.
              </Alert>
            )}
          </CardContent>
        </Card>
        <Stack direction="row" spacing={1}>
          <Button variant="outlined" onClick={() => refresh()}>
            Refresh
          </Button>
          <Button
            variant="contained"
            onClick={async () => {
              try {
                const { data } = await api.post("/settings/smtp/", {});
                enqueueSnackbar(
                  data.sent ? `Tenant SMTP test → ${data.to}` : "Tenant SMTP send failed",
                  { variant: data.sent ? "success" : "error" }
                );
              } catch {
                enqueueSnackbar("SMTP test failed — configure tenant or platform SMTP", {
                  variant: "error",
                });
              }
            }}
          >
            Test tenant SMTP
          </Button>
          <Button
            variant="contained"
            color="secondary"
            onClick={async () => {
              try {
                const { data } = await api.post("/ops/backup/", {});
                enqueueSnackbar(`Backup: ${data.backup}`, { variant: "success" });
              } catch (e: unknown) {
                const detail =
                  (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
                  "Backup failed";
                enqueueSnackbar(String(detail), { variant: "error" });
              }
            }}
          >
            Create backup
          </Button>
        </Stack>
      </Stack>
    </ModuleGate>
  );
}
