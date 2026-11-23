"use client";

import { useEffect, useState } from "react";
import {
  Alert,
  Button,
  Card,
  CardContent,
  Checkbox,
  FormControlLabel,
  Stack,
  TextField,
} from "@mui/material";
import PageHeader from "@/components/PageHeader";
import PlatformGate from "@/components/PlatformGate";
import api from "@/lib/api";
import { useSnackbar } from "notistack";
import { useAppSelector } from "@/store/hooks";

type SmtpForm = {
  host: string;
  port: string;
  username: string;
  password: string;
  use_tls: boolean;
  use_ssl: boolean;
  from_email: string;
  from_name: string;
  reply_to: string;
  is_active: boolean;
  password_set?: boolean;
};

const empty: SmtpForm = {
  host: "",
  port: "587",
  username: "",
  password: "",
  use_tls: true,
  use_ssl: false,
  from_email: "",
  from_name: "SI-ERP",
  reply_to: "",
  is_active: false,
};

export default function PlatformSmtpPage() {
  const user = useAppSelector((s) => s.auth.user);
  const { enqueueSnackbar } = useSnackbar();
  const [smtp, setSmtp] = useState<SmtpForm>(empty);
  const [testTo, setTestTo] = useState("");
  const [saving, setSaving] = useState(false);
  const [forbidden, setForbidden] = useState(false);

  const load = async () => {
    try {
      const { data } = await api.get("/platform/smtp/");
      setForbidden(false);
      setSmtp({
        host: data.host || "",
        port: String(data.port || 587),
        username: data.username || "",
        password: "",
        use_tls: !!data.use_tls,
        use_ssl: !!data.use_ssl,
        from_email: data.from_email || "",
        from_name: data.from_name || "SI-ERP",
        reply_to: data.reply_to || "",
        is_active: !!data.is_active,
        password_set: !!data.password_set,
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
      <PlatformGate capability="smtp">
        <Stack spacing={2}>
          <PageHeader
            title="Platform SMTP"
            subtitle="System emails for signup, billing and platform alerts"
          />
          <Alert severity="warning">
            Only the platform owner can manage system SMTP.
            {user?.username ? ` Signed in as ${user.username}.` : ""}
          </Alert>
        </Stack>
      </PlatformGate>
    );
  }

  return (
    <PlatformGate capability="smtp">
    <Stack spacing={2}>
      <PageHeader
        title="Platform SMTP"
        subtitle="System mailer used for signup, billing notices and fallback when a tenant has no SMTP"
      />
      <Card>
        <CardContent>
          <Alert severity="info" sx={{ mb: 2 }}>
            This is the SaaS platform SMTP — not tenant-specific. Tenants configure their own under
            Settings → Email.
            {smtp.password_set ? " Password is set (leave blank to keep)." : ""}
          </Alert>
          <Stack spacing={1.5} maxWidth={560}>
            <TextField
              label="SMTP host"
              value={smtp.host}
              onChange={(e) => setSmtp({ ...smtp, host: e.target.value })}
            />
            <TextField
              label="Port"
              type="number"
              value={smtp.port}
              onChange={(e) => setSmtp({ ...smtp, port: e.target.value })}
            />
            <TextField
              label="Username"
              value={smtp.username}
              onChange={(e) => setSmtp({ ...smtp, username: e.target.value })}
            />
            <TextField
              label="Password"
              type="password"
              value={smtp.password}
              onChange={(e) => setSmtp({ ...smtp, password: e.target.value })}
            />
            <TextField
              label="From email"
              value={smtp.from_email}
              onChange={(e) => setSmtp({ ...smtp, from_email: e.target.value })}
            />
            <TextField
              label="From name"
              value={smtp.from_name}
              onChange={(e) => setSmtp({ ...smtp, from_name: e.target.value })}
            />
            <TextField
              label="Reply-To"
              value={smtp.reply_to}
              onChange={(e) => setSmtp({ ...smtp, reply_to: e.target.value })}
            />
            <FormControlLabel
              control={
                <Checkbox
                  checked={smtp.use_tls}
                  onChange={(e) => setSmtp({ ...smtp, use_tls: e.target.checked })}
                />
              }
              label="Use TLS"
            />
            <FormControlLabel
              control={
                <Checkbox
                  checked={smtp.use_ssl}
                  onChange={(e) => setSmtp({ ...smtp, use_ssl: e.target.checked })}
                />
              }
              label="Use SSL"
            />
            <FormControlLabel
              control={
                <Checkbox
                  checked={smtp.is_active}
                  onChange={(e) => setSmtp({ ...smtp, is_active: e.target.checked })}
                />
              }
              label="Active"
            />
            <Stack direction="row" spacing={1}>
              <Button
                variant="contained"
                disabled={saving}
                onClick={async () => {
                  setSaving(true);
                  try {
                    const payload: Record<string, unknown> = {
                      ...smtp,
                      port: Number(smtp.port) || 587,
                    };
                    delete payload.password_set;
                    if (!smtp.password) delete payload.password;
                    await api.put("/platform/smtp/", payload);
                    enqueueSnackbar("Platform SMTP saved", { variant: "success" });
                    load();
                  } catch {
                    enqueueSnackbar("Save failed", { variant: "error" });
                  } finally {
                    setSaving(false);
                  }
                }}
              >
                Save platform SMTP
              </Button>
              <TextField
                size="small"
                label="Test to"
                value={testTo}
                onChange={(e) => setTestTo(e.target.value)}
              />
              <Button
                variant="outlined"
                onClick={async () => {
                  try {
                    const { data } = await api.post("/platform/smtp/", { email: testTo });
                    enqueueSnackbar(
                      data.sent ? `Test sent to ${data.to}` : "Send failed",
                      { variant: data.sent ? "success" : "error" }
                    );
                  } catch {
                    enqueueSnackbar("Test failed", { variant: "error" });
                  }
                }}
              >
                Send test
              </Button>
            </Stack>
          </Stack>
        </CardContent>
      </Card>
    </Stack>
    </PlatformGate>
  );
}
