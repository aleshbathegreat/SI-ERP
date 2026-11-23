"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Alert,
  Chip,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import CrudTable from "@/components/crud/CrudTable";
import ConfirmDialog from "@/components/crud/ConfirmDialog";
import PlatformGate from "@/components/PlatformGate";
import { useRouter } from "next/navigation";
import api from "@/lib/api";
import { unwrapList } from "@/lib/crudApi";
import { useSnackbar } from "notistack";
import BlockIcon from "@mui/icons-material/Block";
import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutlined";

type Staff = {
  id: number;
  user: number;
  username: string;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
  title: string;
  notes: string;
  capabilities: string[];
};

const basePath = "/platform/staff";
const resourcePath = "/platform/staff/";

const ROLE_OPTIONS = [
  { value: "", label: "All roles" },
  { value: "finance", label: "Finance" },
  { value: "sales", label: "Sales" },
  { value: "support", label: "Support" },
  { value: "technical", label: "Technical" },
  { value: "owner", label: "Owner" },
];

const STATUS_OPTIONS = [
  { value: "", label: "All statuses" },
  { value: "true", label: "Active" },
  { value: "false", label: "Inactive" },
];

export default function PlatformStaffPage() {
  const router = useRouter();
  const { enqueueSnackbar } = useSnackbar();
  const [rows, setRows] = useState<Staff[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [q, setQ] = useState("");
  const [role, setRole] = useState("");
  const [status, setStatus] = useState("");
  const [confirm, setConfirm] = useState<{ type: "one" | "bulk"; row?: Staff } | null>(
    null
  );
  const [confirmToggle, setConfirmToggle] = useState<Staff | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    const params: Record<string, string> = {};
    if (q.trim()) params.search = q.trim();
    if (role) params.role = role;
    if (status) params.is_active = status;
    api
      .get(resourcePath, { params })
      .then((r) => {
        setRows(unwrapList<Staff>(r.data));
        setSelectedIds([]);
      })
      .catch(() => enqueueSnackbar("Unable to load staff", { variant: "error" }))
      .finally(() => setLoading(false));
  }, [enqueueSnackbar, q, role, status]);

  useEffect(() => {
    const t = setTimeout(load, q ? 250 : 0);
    return () => clearTimeout(t);
  }, [load, q]);

  const runToggle = async () => {
    if (!confirmToggle) return;
    setBusy(true);
    try {
      await api.patch(`/platform/staff/${confirmToggle.id}/`, {
        is_active: !confirmToggle.is_active,
      });
      enqueueSnackbar(
        confirmToggle.is_active ? "Staff deactivated" : "Staff activated",
        { variant: "success" }
      );
      setConfirmToggle(null);
      load();
    } catch {
      enqueueSnackbar("Update failed", { variant: "error" });
    } finally {
      setBusy(false);
    }
  };

  const runConfirmDelete = async () => {
    if (!confirm) return;
    setSaving(true);
    try {
      if (confirm.type === "one" && confirm.row) {
        await api.delete(`/platform/staff/${confirm.row.id}/`);
        enqueueSnackbar("Staff deleted", { variant: "success" });
      } else {
        const { data } = await api.post<{ deleted: number }>(
          "/platform/staff/bulk-delete/",
          { ids: selectedIds }
        );
        enqueueSnackbar(`${data.deleted} staff deleted`, { variant: "success" });
      }
      setConfirm(null);
      load();
    } catch {
      enqueueSnackbar("Could not delete staff", { variant: "error" });
    } finally {
      setSaving(false);
    }
  };

  return (
    <PlatformGate capability="staff">
      <Alert severity="info" sx={{ mb: 2 }}>
        Django superuser is always platform owner. Staff accounts are scoped by role
        capabilities (finance / sales / support / technical).
      </Alert>
      <CrudTable
        title="Platform staff"
        subtitle="Platform operator accounts"
        rows={rows}
        loading={loading}
        selectedIds={selectedIds}
        onToggleAll={(checked) =>
          setSelectedIds(checked ? rows.map((r) => r.id) : [])
        }
        onToggleOne={(id, checked) =>
          setSelectedIds((prev) =>
            checked ? [...new Set([...prev, id])] : prev.filter((x) => x !== id)
          )
        }
        onRefresh={load}
        onCreate={() => router.push(`${basePath}/new`)}
        onEdit={(row) => router.push(`${basePath}/${row.id}/edit`)}
        onView={(row) => router.push(`${basePath}/${row.id}`)}
        onDeleteOne={(row) => setConfirm({ type: "one", row })}
        onBulkDelete={() => {
          if (selectedIds.length) setConfirm({ type: "bulk" });
        }}
        createLabel="Add staff"
        emptyTitle="No platform staff match"
        toolbarExtra={
          <>
            <TextField
              size="small"
              label="Search"
              placeholder="Name, email, title…"
              value={q}
              onChange={(e) => setQ(e.target.value)}
            />
            <FormControl size="small">
              <InputLabel id="staff-role-filter">Role</InputLabel>
              <Select
                labelId="staff-role-filter"
                label="Role"
                value={role}
                onChange={(e) => setRole(e.target.value)}
              >
                {ROLE_OPTIONS.map((o) => (
                  <MenuItem key={o.value || "all"} value={o.value}>
                    {o.label}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <FormControl size="small">
              <InputLabel id="staff-status-filter">Status</InputLabel>
              <Select
                labelId="staff-status-filter"
                label="Status"
                value={status}
                onChange={(e) => setStatus(e.target.value)}
              >
                {STATUS_OPTIONS.map((o) => (
                  <MenuItem key={o.value || "all"} value={o.value}>
                    {o.label}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </>
        }
        getRowActions={(row) => [
          {
            key: "toggle",
            label: row.is_active ? "Deactivate" : "Activate",
            icon: row.is_active ? (
              <BlockIcon fontSize="small" />
            ) : (
              <CheckCircleOutlineIcon fontSize="small" />
            ),
            onClick: () => setConfirmToggle(row),
            dividerBefore: true,
          },
        ]}
        columns={[
          {
            key: "user",
            header: "User",
            render: (r) => (
              <>
                <strong>{r.full_name || r.username}</strong>
                <Typography variant="caption" display="block" color="text.secondary">
                  {r.username} · {r.email}
                </Typography>
              </>
            ),
          },
          {
            key: "role",
            header: "Role",
            render: (r) => <Chip size="small" label={r.role} color="primary" />,
          },
          { key: "title", header: "Title", render: (r) => r.title || "—" },
          {
            key: "caps",
            header: "Capabilities",
            render: (r) => (
              <Typography variant="caption">{(r.capabilities || []).join(", ")}</Typography>
            ),
          },
          {
            key: "status",
            header: "Status",
            render: (r) => (
              <Chip
                size="small"
                color={r.is_active ? "success" : "default"}
                label={r.is_active ? "active" : "off"}
              />
            ),
          },
        ]}
      />

      <ConfirmDialog
        open={!!confirm}
        title={confirm?.type === "bulk" ? "Delete selected staff?" : "Delete staff member?"}
        message={
          confirm?.type === "bulk"
            ? `Remove ${selectedIds.length} staff record(s)? User accounts are kept.`
            : `Remove staff “${confirm?.row?.username}”?`
        }
        confirmLabel="Delete"
        loading={saving}
        onClose={() => setConfirm(null)}
        onConfirm={runConfirmDelete}
      />

      <ConfirmDialog
        open={!!confirmToggle}
        title={confirmToggle?.is_active ? "Deactivate staff?" : "Activate staff?"}
        message={
          confirmToggle?.is_active
            ? `Deactivate “${confirmToggle?.username}”? They will lose platform access.`
            : `Activate “${confirmToggle?.username}”?`
        }
        confirmLabel={confirmToggle?.is_active ? "Deactivate" : "Activate"}
        danger={!!confirmToggle?.is_active}
        loading={busy}
        onClose={() => setConfirmToggle(null)}
        onConfirm={runToggle}
      />
    </PlatformGate>
  );
}
