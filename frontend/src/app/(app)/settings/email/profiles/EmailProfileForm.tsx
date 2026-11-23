"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import {
  Button,
  Checkbox,
  FormControlLabel,
  MenuItem,
  TextField,
} from "@mui/material";
import EditIcon from "@mui/icons-material/Edit";
import FormPageShell from "@/components/crud/FormPageShell";
import ModuleGate from "@/components/ModuleGate";
import { useEntityForm, type FormMode } from "@/hooks/useEntityForm";
import { usePermissions } from "@/hooks/usePermissions";
import { listResource } from "@/lib/crudApi";

const moduleKey = "settings.email";
const basePath = "/settings/email/profiles";
const listPath = "/settings/email";
const resourcePath = "/settings/email-profiles/";

const PURPOSES = [
  ["general", "General"],
  ["workflow", "Workflow / Approvals"],
  ["hr", "HR / ESS"],
  ["finance", "Finance"],
  ["payroll", "Payroll"],
  ["billing", "Billing"],
  ["crm", "CRM"],
] as const;

type Person = {
  id: number;
  email?: string;
  username?: string;
  first_name?: string;
  last_name?: string;
  employee_code?: string;
};

const empty = {
  name: "",
  email: "",
  purpose: "general",
  reply_to: "",
  signature: "",
  owner_type: "shared",
  user: "" as number | "",
  employee: "" as number | "",
  inbound: "none",
  imap_host: "",
  imap_port: "993",
  imap_username: "",
  imap_password: "",
  imap_use_ssl: true,
  is_default: false,
  is_active: true,
};

function personLabel(row: Person) {
  const name = `${row.first_name || ""} ${row.last_name || ""}`.trim();
  if (row.employee_code) return `${row.employee_code} · ${name || row.email || ""}`;
  return name || row.email || row.username || String(row.id);
}

export default function EmailProfileForm({ mode }: { mode: FormMode }) {
  const params = useParams();
  const id = mode === "create" ? undefined : String(params.id);
  const { canChange } = usePermissions();
  const [users, setUsers] = useState<Person[]>([]);
  const [employees, setEmployees] = useState<Person[]>([]);
  const { form, setForm, loading, saving, save, readOnly } = useEntityForm({
    resourcePath,
    entityLabel: "Email profile",
    basePath: listPath,
    mode,
    id,
    empty,
    mapLoaded: (row) => ({
      name: String(row.name ?? ""),
      email: String(row.email ?? ""),
      purpose: String(row.purpose ?? "general"),
      reply_to: String(row.reply_to ?? ""),
      signature: String(row.signature ?? ""),
      owner_type: String(row.owner_type ?? "shared"),
      user: (row.user as number | null) || "",
      employee: (row.employee as number | null) || "",
      inbound: String(row.inbound ?? "none"),
      imap_host: String(row.imap_host ?? ""),
      imap_port: String(row.imap_port ?? 993),
      imap_username: String(row.imap_username ?? ""),
      imap_password: "",
      imap_use_ssl: row.imap_use_ssl !== false,
      is_default: !!row.is_default,
      is_active: !!row.is_active,
    }),
    mapPayload: (current) => {
      const payload: Record<string, unknown> = {
        ...current,
        user: current.owner_type === "user" ? current.user || null : null,
        employee: current.owner_type === "employee" ? current.employee || null : null,
        imap_port: Number(current.imap_port) || 993,
      };
      if (!current.imap_password) delete payload.imap_password;
      return payload;
    },
  });

  useEffect(() => {
    listResource<Person>("/settings/users/").then(setUsers).catch(() => setUsers([]));
    listResource<Person>("/hr/employees/").then(setEmployees).catch(() => setEmployees([]));
  }, []);

  const title =
    mode === "create" ? "Add mailbox" : mode === "edit" ? "Edit mailbox" : "View mailbox";

  return (
    <ModuleGate module={moduleKey}>
      <FormPageShell
        title={title}
        backHref={listPath}
        backLabel="Back to email settings"
        mode={mode}
        loading={loading}
        saving={saving}
        onSubmit={save}
        extraActions={
          mode === "view" && canChange(moduleKey) && id ? (
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
          label="Display name"
          value={form.name}
          disabled={readOnly}
          onChange={(e) => setForm({ ...form, name: e.target.value })}
        />
        <TextField
          label="Email"
          value={form.email}
          disabled={readOnly}
          onChange={(e) => setForm({ ...form, email: e.target.value })}
        />
        <TextField
          select
          label="Used for"
          value={form.purpose}
          disabled={readOnly}
          onChange={(e) => setForm({ ...form, purpose: e.target.value })}
        >
          {PURPOSES.map(([value, label]) => (
            <MenuItem key={value} value={value}>
              {label}
            </MenuItem>
          ))}
        </TextField>
        <TextField
          select
          label="Mailbox belongs to"
          value={form.owner_type}
          disabled={readOnly}
          onChange={(e) =>
            setForm({
              ...form,
              owner_type: e.target.value,
              user: e.target.value === "user" ? form.user : "",
              employee: e.target.value === "employee" ? form.employee : "",
            })
          }
          helperText="Shared is a company address. A full user or an employee can also have their own."
        >
          <MenuItem value="shared">Shared mailbox</MenuItem>
          <MenuItem value="user">Full user</MenuItem>
          <MenuItem value="employee">Employee</MenuItem>
        </TextField>
        {form.owner_type === "user" ? (
          <TextField
            select
            label="User"
            value={form.user}
            disabled={readOnly}
            onChange={(e) => setForm({ ...form, user: Number(e.target.value) })}
          >
            {users.map((row) => (
              <MenuItem key={row.id} value={row.id}>
                {personLabel(row)}
              </MenuItem>
            ))}
          </TextField>
        ) : null}
        {form.owner_type === "employee" ? (
          <TextField
            select
            label="Employee"
            value={form.employee}
            disabled={readOnly}
            onChange={(e) => setForm({ ...form, employee: Number(e.target.value) })}
            helperText="The employee does not need a separate login. A linked user can open this mailbox."
          >
            {employees.map((row) => (
              <MenuItem key={row.id} value={row.id}>
                {personLabel(row)}
              </MenuItem>
            ))}
          </TextField>
        ) : null}
        <TextField
          label="Reply-To"
          value={form.reply_to}
          disabled={readOnly}
          onChange={(e) => setForm({ ...form, reply_to: e.target.value })}
        />
        <TextField
          label="Signature"
          value={form.signature}
          disabled={readOnly}
          multiline
          minRows={2}
          onChange={(e) => setForm({ ...form, signature: e.target.value })}
        />
        <TextField
          select
          label="Receive mail"
          value={form.inbound}
          disabled={readOnly}
          onChange={(e) => setForm({ ...form, inbound: e.target.value })}
          helperText="Send uses tenant SMTP or Microsoft 365. Microsoft 365 inbox needs Mail.Read. IMAP covers Google, Zoho, and other hosts."
        >
          <MenuItem value="none">Send only</MenuItem>
          <MenuItem value="graph">Microsoft 365 inbox</MenuItem>
          <MenuItem value="imap">IMAP inbox</MenuItem>
        </TextField>
        {form.inbound === "imap" ? (
          <>
            <TextField
              label="IMAP host"
              value={form.imap_host}
              disabled={readOnly}
              onChange={(e) => setForm({ ...form, imap_host: e.target.value })}
            />
            <TextField
              label="IMAP port"
              type="number"
              value={form.imap_port}
              disabled={readOnly}
              onChange={(e) => setForm({ ...form, imap_port: e.target.value })}
              slotProps={{ htmlInput: { min: 1, max: 65535 }, inputLabel: { shrink: true } }}
            />
            <TextField
              label="IMAP username"
              value={form.imap_username}
              disabled={readOnly}
              onChange={(e) => setForm({ ...form, imap_username: e.target.value })}
              helperText="Leave blank to use the mailbox email"
            />
            <TextField
              label="IMAP password"
              type="password"
              value={form.imap_password}
              disabled={readOnly}
              onChange={(e) => setForm({ ...form, imap_password: e.target.value })}
              helperText="Leave blank to keep the saved password"
            />
            <FormControlLabel
              control={
                <Checkbox
                  checked={form.imap_use_ssl}
                  disabled={readOnly}
                  onChange={(e) => setForm({ ...form, imap_use_ssl: e.target.checked })}
                />
              }
              label="IMAP SSL"
            />
          </>
        ) : null}
        <FormControlLabel
          control={
            <Checkbox
              checked={form.is_default}
              disabled={readOnly}
              onChange={(e) => setForm({ ...form, is_default: e.target.checked })}
            />
          }
          label="Default for system mail"
        />
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
      </FormPageShell>
    </ModuleGate>
  );
}
