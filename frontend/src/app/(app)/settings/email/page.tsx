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
  Typography,
} from "@mui/material";
import CrudTable from "@/components/crud/CrudTable";
import ConfirmDialog from "@/components/crud/ConfirmDialog";
import ModuleGate from "@/components/ModuleGate";
import PageHeader from "@/components/PageHeader";
import { useCrudList } from "@/hooks/useCrudList";
import { usePermissions } from "@/hooks/usePermissions";
import api from "@/lib/api";
import { useSnackbar } from "notistack";

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

type Profile = {
  id: number;
  name: string;
  email: string;
  purpose: string;
  reply_to: string;
  owner_label?: string;
  inbound?: string;
  is_default: boolean;
  is_active: boolean;
};

const emptySmtp: SmtpForm = {
  host: "",
  port: "587",
  username: "",
  password: "",
  use_tls: true,
  use_ssl: false,
  from_email: "",
  from_name: "",
  reply_to: "",
  is_active: false,
};

const moduleKey = "settings.email";
const profilesBasePath = "/settings/email/profiles";

export default function TenantEmailSettingsPage() {
  const { canAdd, canChange, canDelete } = usePermissions();
  const { enqueueSnackbar } = useSnackbar();
  const [smtp, setSmtp] = useState<SmtpForm>(emptySmtp);
  const [testTo, setTestTo] = useState("");
  const [saving, setSaving] = useState(false);
  const crud = useCrudList<Profile>(
    "/settings/email-profiles/",
    "Email profile",
    profilesBasePath
  );

  const loadSmtp = async () => {
    const { data } = await api.get("/settings/smtp/");
    setSmtp({
      host: data.host || "",
      port: String(data.port || 587),
      username: data.username || "",
      password: "",
      use_tls: !!data.use_tls,
      use_ssl: !!data.use_ssl,
      from_email: data.from_email || "",
      from_name: data.from_name || "",
      reply_to: data.reply_to || "",
      is_active: !!data.is_active,
      password_set: !!data.password_set,
    });
  };

  useEffect(() => {
    loadSmtp().catch(() => undefined);
  }, []);

  return (
    <ModuleGate module={moduleKey}>
      <PageHeader
        title="Tenant email settings"
        subtitle="Organization SMTP, and a mailbox for the company, each full user, or an employee"
        moduleKey={moduleKey}
      />

      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Tenant SMTP
          </Typography>
          <Alert severity="info" sx={{ mb: 2 }}>
            When active, workflow / HR / finance emails send via your SMTP. Otherwise platform
            system SMTP is used as fallback.
            {smtp.password_set ? " Password is set (leave blank to keep)." : ""}
          </Alert>
          <Stack spacing={1.5} maxWidth={560}>
            <TextField
              label="SMTP host"
              value={smtp.host}
              disabled={!canChange(moduleKey)}
              onChange={(e) => setSmtp({ ...smtp, host: e.target.value })}
            />
            <TextField
              label="Port"
              type="number"
              value={smtp.port}
              disabled={!canChange(moduleKey)}
              onChange={(e) => setSmtp({ ...smtp, port: e.target.value })}
            />
            <TextField
              label="Username"
              value={smtp.username}
              disabled={!canChange(moduleKey)}
              onChange={(e) => setSmtp({ ...smtp, username: e.target.value })}
            />
            <TextField
              label="Password"
              type="password"
              value={smtp.password}
              disabled={!canChange(moduleKey)}
              onChange={(e) => setSmtp({ ...smtp, password: e.target.value })}
              helperText="Leave blank to keep existing password"
            />
            <TextField
              label="Default from email"
              value={smtp.from_email}
              disabled={!canChange(moduleKey)}
              onChange={(e) => setSmtp({ ...smtp, from_email: e.target.value })}
            />
            <TextField
              label="From name"
              value={smtp.from_name}
              disabled={!canChange(moduleKey)}
              onChange={(e) => setSmtp({ ...smtp, from_name: e.target.value })}
            />
            <TextField
              label="Reply-To"
              value={smtp.reply_to}
              disabled={!canChange(moduleKey)}
              onChange={(e) => setSmtp({ ...smtp, reply_to: e.target.value })}
            />
            <FormControlLabel
              control={
                <Checkbox
                  checked={smtp.use_tls}
                  disabled={!canChange(moduleKey)}
                  onChange={(e) => setSmtp({ ...smtp, use_tls: e.target.checked })}
                />
              }
              label="Use TLS"
            />
            <FormControlLabel
              control={
                <Checkbox
                  checked={smtp.use_ssl}
                  disabled={!canChange(moduleKey)}
                  onChange={(e) => setSmtp({ ...smtp, use_ssl: e.target.checked })}
                />
              }
              label="Use SSL"
            />
            <FormControlLabel
              control={
                <Checkbox
                  checked={smtp.is_active}
                  disabled={!canChange(moduleKey)}
                  onChange={(e) => setSmtp({ ...smtp, is_active: e.target.checked })}
                />
              }
              label="Active (use this SMTP for tenant emails)"
            />
            <Stack direction="row" spacing={1}>
              <Button
                variant="contained"
                disabled={!canChange(moduleKey) || saving}
                onClick={async () => {
                  setSaving(true);
                  try {
                    const payload: Record<string, unknown> = {
                      ...smtp,
                      port: Number(smtp.port) || 587,
                    };
                    delete payload.password_set;
                    if (!smtp.password) delete payload.password;
                    await api.put("/settings/smtp/", payload);
                    enqueueSnackbar("Tenant SMTP saved", { variant: "success" });
                    loadSmtp();
                  } catch {
                    enqueueSnackbar("Save failed", { variant: "error" });
                  } finally {
                    setSaving(false);
                  }
                }}
              >
                Save SMTP
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
                    const { data } = await api.post("/settings/smtp/", { email: testTo });
                    enqueueSnackbar(
                      data.sent ? `Test sent to ${data.to}` : "Send failed — check SMTP",
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

      <CrudTable
        title="Mailboxes"
        subtitle="Shared, a full user, or an employee. Several can be active at once."
        rows={crud.rows}
        loading={crud.loading}
        selectedIds={crud.selectedIds}
        onToggleAll={crud.toggleAll}
        onToggleOne={crud.toggleOne}
        onRefresh={crud.load}
        onCreate={crud.openCreate}
        onEdit={crud.openEdit}
        onView={crud.openView}
        onDeleteOne={crud.askDeleteOne}
        onBulkDelete={crud.askBulkDelete}
        createLabel="Add mailbox"
        canCreate={canAdd(moduleKey)}
        canEdit={canChange(moduleKey)}
        canDelete={canDelete(moduleKey)}
        columns={[
          { key: "name", header: "Name", render: (r) => r.name },
          { key: "email", header: "Email", render: (r) => r.email },
          { key: "purpose", header: "Purpose", render: (r) => r.purpose },
          { key: "owner", header: "Belongs to", render: (r) => r.owner_label || "Shared" },
          { key: "inbound", header: "Receive", render: (r) => r.inbound || "none" },
          {
            key: "default",
            header: "Default",
            render: (r) => (r.is_default ? "Yes" : "—"),
          },
          {
            key: "active",
            header: "Active",
            render: (r) => (r.is_active ? "Yes" : "No"),
          },
        ]}
      />

      <ConfirmDialog
        open={!!crud.confirm}
        title="Delete profile?"
        message="Remove this email profile?"
        confirmLabel="Delete"
        loading={crud.saving}
        onClose={() => crud.setConfirm(null)}
        onConfirm={crud.runConfirmDelete}
      />
    </ModuleGate>
  );
}
