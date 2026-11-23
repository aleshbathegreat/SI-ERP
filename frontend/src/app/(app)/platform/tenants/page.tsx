"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Chip,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import EventAvailableIcon from "@mui/icons-material/EventAvailable";
import BlockIcon from "@mui/icons-material/Block";
import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutlined";
import CrudTable from "@/components/crud/CrudTable";
import ConfirmDialog from "@/components/crud/ConfirmDialog";
import PlatformGate from "@/components/PlatformGate";
import { usePlatformCaps } from "@/hooks/usePlatformCaps";
import api from "@/lib/api";
import { useSnackbar } from "notistack";

type Tenant = {
  id: number;
  name: string;
  code: string;
  brand_name?: string;
  email?: string;
  plan: string;
  plan_status: string;
  package_name?: string | null;
  is_active: boolean;
  trial_ends?: string | null;
  subscription_ends?: string | null;
  grace_days?: number;
  owner?: string | null;
  custom_domain?: string;
  custom_domain_verified?: boolean;
  subscription_open?: boolean;
  days_until_lock?: number | null;
};

type ConfirmKind =
  | { type: "deactivate" | "activate" | "extend" | "bulk_deactivate" | "bulk_activate" | "bulk_extend"; row?: Tenant };

const basePath = "/platform/tenants";

export default function PlatformTenantsPage() {
  const router = useRouter();
  const { enqueueSnackbar } = useSnackbar();
  const { can } = usePlatformCaps();
  const [rows, setRows] = useState<Tenant[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [q, setQ] = useState("");
  const [confirm, setConfirm] = useState<ConfirmKind | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    api
      .get<{ results: Tenant[] }>("/platform/tenants/")
      .then((r) => {
        setRows(r.data.results || []);
        setSelectedIds([]);
      })
      .catch(() => enqueueSnackbar("Unable to load tenants", { variant: "error" }))
      .finally(() => setLoading(false));
  }, [enqueueSnackbar]);

  useEffect(() => {
    load();
  }, [load]);

  const filtered = useMemo(() => {
    if (!q.trim()) return rows;
    const s = q.toLowerCase();
    return rows.filter(
      (t) =>
        t.name.toLowerCase().includes(s) ||
        t.code.toLowerCase().includes(s) ||
        (t.brand_name || "").toLowerCase().includes(s) ||
        (t.email || "").toLowerCase().includes(s)
    );
  }, [rows, q]);

  const patch = async (id: number, data: Record<string, unknown>) => {
    await api.patch("/platform/tenants/", { id, ...data });
  };

  const runConfirm = async () => {
    if (!confirm) return;
    setBusy(true);
    try {
      if (confirm.type === "extend" && confirm.row) {
        await patch(confirm.row.id, {
          extend_days: 14,
          as_trial: confirm.row.plan === "trial",
        });
        enqueueSnackbar("Extended +14 days", { variant: "success" });
      } else if (confirm.type === "deactivate" && confirm.row) {
        await patch(confirm.row.id, { is_active: false });
        enqueueSnackbar("Tenant deactivated", { variant: "success" });
      } else if (confirm.type === "activate" && confirm.row) {
        await patch(confirm.row.id, { is_active: true });
        enqueueSnackbar("Tenant activated", { variant: "success" });
      } else if (confirm.type === "bulk_extend") {
        for (const id of selectedIds) {
          const t = rows.find((r) => r.id === id);
          await patch(id, { extend_days: 14, as_trial: t?.plan === "trial" });
        }
        enqueueSnackbar(`Extended ${selectedIds.length} tenant(s)`, { variant: "success" });
      } else if (confirm.type === "bulk_deactivate") {
        for (const id of selectedIds) await patch(id, { is_active: false });
        enqueueSnackbar(`Deactivated ${selectedIds.length}`, { variant: "success" });
      } else if (confirm.type === "bulk_activate") {
        for (const id of selectedIds) await patch(id, { is_active: true });
        enqueueSnackbar(`Activated ${selectedIds.length}`, { variant: "success" });
      }
      setConfirm(null);
      load();
    } catch {
      enqueueSnackbar("Action failed", { variant: "error" });
    } finally {
      setBusy(false);
    }
  };

  const confirmTitle = () => {
    switch (confirm?.type) {
      case "extend":
      case "bulk_extend":
        return "Extend subscription?";
      case "deactivate":
      case "bulk_deactivate":
        return "Deactivate tenant(s)?";
      case "activate":
      case "bulk_activate":
        return "Activate tenant(s)?";
      default:
        return "Confirm";
    }
  };

  const confirmMessage = () => {
    switch (confirm?.type) {
      case "extend":
        return `Add 14 days to “${confirm.row?.brand_name || confirm.row?.name}”?`;
      case "bulk_extend":
        return `Add 14 days to ${selectedIds.length} selected tenant(s)?`;
      case "deactivate":
        return `Deactivate “${confirm.row?.brand_name || confirm.row?.name}”? Users will lose access.`;
      case "bulk_deactivate":
        return `Deactivate ${selectedIds.length} tenant(s)?`;
      case "activate":
        return `Activate “${confirm.row?.brand_name || confirm.row?.name}”?`;
      case "bulk_activate":
        return `Activate ${selectedIds.length} tenant(s)?`;
      default:
        return "";
    }
  };

  return (
    <PlatformGate capability="tenants">
      <CrudTable
        title="Tenants"
        subtitle="Organizations on this platform"
        rows={filtered}
        loading={loading}
        selectedIds={selectedIds}
        onToggleAll={(checked) =>
          setSelectedIds(checked ? filtered.map((r) => r.id) : [])
        }
        onToggleOne={(id, checked) =>
          setSelectedIds((prev) =>
            checked ? [...new Set([...prev, id])] : prev.filter((x) => x !== id)
          )
        }
        onRefresh={load}
        onView={(row) => router.push(`${basePath}/${row.id}`)}
        canCreate={false}
        canEdit={false}
        canDelete={false}
        canSelect
        toolbarExtra={
          <TextField
            size="small"
            label="Search"
            placeholder="Name, code, email…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
        }
        bulkActions={[
          ...(can("tenants.extend")
            ? [
                {
                  key: "extend",
                  label: "Extend +14d",
                  icon: <EventAvailableIcon />,
                  onClick: () => setConfirm({ type: "bulk_extend" }),
                },
              ]
            : []),
          {
            key: "activate",
            label: "Activate",
            icon: <CheckCircleOutlineIcon />,
            onClick: () => setConfirm({ type: "bulk_activate" }),
          },
          {
            key: "deactivate",
            label: "Deactivate",
            icon: <BlockIcon />,
            onClick: () => setConfirm({ type: "bulk_deactivate" }),
          },
        ]}
        getRowActions={(row) => [
          ...(can("tenants.extend")
            ? [
                {
                  key: "extend",
                  label: "Extend +14 days",
                  icon: <EventAvailableIcon fontSize="small" />,
                  onClick: () => setConfirm({ type: "extend", row }),
                },
              ]
            : []),
          {
            key: "toggle",
            label: row.is_active ? "Deactivate" : "Activate",
            icon: row.is_active ? (
              <BlockIcon fontSize="small" />
            ) : (
              <CheckCircleOutlineIcon fontSize="small" />
            ),
            onClick: () =>
              setConfirm({
                type: row.is_active ? "deactivate" : "activate",
                row,
              }),
            dividerBefore: true,
            danger: row.is_active,
          },
        ]}
        emptyTitle="No tenants found"
        columns={[
          {
            key: "tenant",
            header: "Tenant",
            render: (t) => (
              <>
                <strong>{t.brand_name || t.name}</strong>
                <Typography variant="caption" display="block" color="text.secondary">
                  {t.code}
                  {t.email ? ` · ${t.email}` : ""}
                </Typography>
              </>
            ),
          },
          { key: "owner", header: "Owner", render: (t) => t.owner || "—" },
          { key: "plan", header: "Plan", render: (t) => t.plan },
          { key: "pkg", header: "Package", render: (t) => t.package_name || "—" },
          {
            key: "status",
            header: "Status",
            render: (t) => (
              <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap>
                <Chip
                  size="small"
                  color={t.is_active ? "success" : "default"}
                  label={t.is_active ? "active" : "off"}
                />
                <Chip size="small" variant="outlined" label={t.plan_status} />
              </Stack>
            ),
          },
          {
            key: "domain",
            header: "Domain",
            render: (t) =>
              t.custom_domain ? (
                <Chip
                  size="small"
                  variant="outlined"
                  color={t.custom_domain_verified ? "success" : "warning"}
                  label={t.custom_domain}
                />
              ) : (
                "—"
              ),
          },
        ]}
      />

      <ConfirmDialog
        open={!!confirm}
        title={confirmTitle()}
        message={confirmMessage()}
        confirmLabel={
          confirm?.type?.includes("deactivate")
            ? "Deactivate"
            : confirm?.type?.includes("activate")
              ? "Activate"
              : "Extend"
        }
        danger={!!confirm?.type?.includes("deactivate")}
        loading={busy}
        onClose={() => setConfirm(null)}
        onConfirm={runConfirm}
      />
    </PlatformGate>
  );
}
