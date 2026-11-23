"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  Alert,
  Box,
  Button,
  Checkbox,
  Chip,
  Collapse,
  FormControlLabel,
  IconButton,
  Stack,
  Tab,
  Tabs,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
  Tooltip,
  Typography,
} from "@mui/material";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import DevicesIcon from "@mui/icons-material/Devices";
import ExpandLessIcon from "@mui/icons-material/ExpandLess";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import LoginIcon from "@mui/icons-material/Login";
import LogoutIcon from "@mui/icons-material/Logout";
import SyncIcon from "@mui/icons-material/Sync";
import CrudTable from "@/components/crud/CrudTable";
import ConfirmDialog from "@/components/crud/ConfirmDialog";
import ModuleGate from "@/components/ModuleGate";
import PageHeader from "@/components/PageHeader";
import { useCrudList } from "@/hooks/useCrudList";
import { usePermissions } from "@/hooks/usePermissions";
import { formatDate } from "@/lib/format";
import api from "@/lib/api";
import { errorSnackbarOpts, getApiErrorMessage } from "@/lib/apiError";
import { useSnackbar } from "notistack";

type Row = {
  id: number;
  employee_name?: string;
  employee_code?: string;
  employee: string | number;
  work_date: string | number;
  check_in: string | number;
  check_out: string | number;
  status: string | number;
  source?: string;
  notes: string | number;
};

type DeviceRow = {
  id: number;
  device_id: string;
  connector_key: string;
  connector_name?: string;
  vendor?: string;
  make: string;
  model_name: string;
  location: string;
  connection_mode: string;
  is_active: boolean;
  last_sync_at?: string | null;
  last_sync_status?: string;
  last_sync_message?: string;
};

type ConnectorUsage = {
  devices: number;
  active: number;
  errors: number;
  ok: number;
  last_sync_at: string | null;
  health: "ok" | "error" | "idle" | "unused";
  device_ids: string[];
};

type Connector = {
  key: string;
  vendor: string;
  name: string;
  models: string;
  modes: string[];
  protocol: string;
  tier: string;
  category?: string;
  docs: string;
  entitled: boolean;
  status?: string;
  capabilities?: {
    push?: boolean;
    pull?: boolean;
    cloud?: boolean;
    csv?: boolean;
    live_pull_agent?: boolean;
    webhook_auth?: boolean;
  };
  setup_steps?: string[];
  webhook_path?: string;
  sample_payload?: Record<string, unknown>;
  sample_csv_header?: string;
  usage?: ConnectorUsage;
};

type CatalogSummary = {
  catalog_total: number;
  entitled: number;
  locked: number;
  connectors_in_use: number;
  healthy: number;
  degraded: number;
  idle: number;
};

type CatalogIntegration = {
  webhook_path: string;
  webhook_auth_header: string;
  sample_payload: Record<string, unknown>;
  csv_header: string;
};

type ConnectorCatalog = {
  module_enabled: boolean;
  max_devices: number | null;
  devices_used: number;
  connectors: Connector[];
  summary?: CatalogSummary;
  integration?: CatalogIntegration;
};

const healthColor = (
  h: string
): "default" | "success" | "error" | "warning" | "info" => {
  if (h === "ok") return "success";
  if (h === "error") return "error";
  if (h === "idle") return "warning";
  return "default";
};

const statusColor = (s: string): "default" | "info" | "warning" | "success" | "error" => {
  if (s === "present" || s === "ok" || s === "wfh" || s === "regularized") return "success";
  if (s === "absent" || s === "error") return "error";
  if (s === "late" || s === "early_leave" || s === "half_day") return "warning";
  if (s === "exception" || s === "exempt" || s === "on_leave" || s === "holiday") return "info";
  return "default";
};

type TodayRow = {
  employee: number;
  employee_code: string;
  employee_name: string;
  is_attendance_free: boolean;
  record_id: number | null;
  check_in: string | null;
  check_out: string | null;
  status: string;
  late_minutes: number;
  worked_minutes: number;
};

function Kpi({ label, value }: { label: string; value: string }) {
  return (
    <Box
      sx={{
        flex: 1,
        minWidth: 100,
        px: 1.5,
        py: 1,
        borderBottom: "2px solid",
        borderColor: "divider",
      }}
    >
      <Typography variant="caption" color="text.secondary">
        {label}
      </Typography>
      <Typography variant="h6" fontWeight={700}>
        {value}
      </Typography>
    </Box>
  );
}

export default function Page() {
  const moduleKey = "hr.attendance";
  const devicesModule = "hr.attendance_devices";
  const { canAdd, canChange, canDelete, canView } = usePermissions();
  // canAdd used for today punch board
  const router = useRouter();
  const search = useSearchParams();
  const tabParam = search.get("tab");
  const tabIndex = (() => {
    if (tabParam === "today") return 0;
    if (tabParam === "records" || !tabParam) return 1;
    if (tabParam === "devices") return 2;
    if (tabParam === "connectors") return 3;
    if (tabParam === "policy") return 4;
    if (tabParam === "requests") return 5;
    return 1;
  })();
  const [tab, setTab] = useState(tabIndex);
  const { enqueueSnackbar } = useSnackbar();
  const [corrections, setCorrections] = useState<
    {
      id: number;
      employee_code?: string;
      employee_name?: string;
      work_date: string;
      requested_check_in?: string | null;
      requested_check_out?: string | null;
      reason: string;
      status: string;
    }[]
  >([]);
  useEffect(() => {
    if (tab !== 5) return;
    api
      .get("/hr/attendance-regularizations/", { params: { status: "pending" } })
      .then(({ data }) => setCorrections(Array.isArray(data) ? data : data.results || []))
      .catch(() => setCorrections([]));
  }, [tab]);

  const crud = useCrudList<Row>("/hr/attendance/", "Attendance", "/hr/attendance");
  const devicesCrud = useCrudList<DeviceRow>(
    "/hr/attendance-devices/",
    "Device",
    "/hr/attendance/devices"
  );

  const [catalog, setCatalog] = useState<ConnectorCatalog | null>(null);
  const [connFilter, setConnFilter] = useState<"all" | "entitled" | "in_use" | "locked">(
    "all"
  );
  const [connQuery, setConnQuery] = useState("");
  const [connExpanded, setConnExpanded] = useState<string | null>(null);
  const [today, setToday] = useState<{
    work_date: string;
    totals: {
      headcount: number;
      present: number;
      absent: number;
      exempt: number;
      on_leave?: number;
      holiday?: number;
    };
    rows: TodayRow[];
  } | null>(null);
  const [policy, setPolicy] = useState<Record<string, unknown> | null>(null);
  const [policySaving, setPolicySaving] = useState(false);
  const [holidays, setHolidays] = useState<
    { id: number; name: string; holiday_date: string; is_optional: boolean }[]
  >([]);
  const [newHoliday, setNewHoliday] = useState({
    name: "",
    holiday_date: "",
    is_optional: false,
  });
  const [reconciling, setReconciling] = useState(false);

  const loadCatalog = useCallback(() => {
    api
      .get<ConnectorCatalog>("/hr/attendance/connectors/")
      .then((r) => setCatalog(r.data))
      .catch(() => setCatalog(null));
  }, []);

  const copyText = useCallback(
    async (label: string, value: string) => {
      try {
        await navigator.clipboard.writeText(value);
        enqueueSnackbar(`${label} copied`, { variant: "success" });
      } catch {
        enqueueSnackbar(`Could not copy ${label}`, { variant: "error" });
      }
    },
    [enqueueSnackbar]
  );

  const filteredConnectors = useMemo(() => {
    if (!catalog) return [];
    const q = connQuery.trim().toLowerCase();
    return catalog.connectors.filter((c) => {
      if (connFilter === "entitled" && !c.entitled) return false;
      if (connFilter === "locked" && c.entitled) return false;
      if (connFilter === "in_use" && !(c.usage && c.usage.devices > 0)) return false;
      if (!q) return true;
      const hay = [c.vendor, c.name, c.key, c.models, c.protocol, c.tier, c.category]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      return hay.includes(q);
    });
  }, [catalog, connFilter, connQuery]);

  const loadToday = useCallback(() => {
    api
      .get<{
        work_date: string;
        totals: { headcount: number; present: number; absent: number; exempt: number };
        rows: TodayRow[];
      }>("/hr/attendance/today/")
      .then((r) => setToday(r.data))
      .catch(() => setToday(null));
  }, []);

  const loadPolicy = useCallback(() => {
    api
      .get<Record<string, unknown>>("/hr/attendance/policy/")
      .then((r) => setPolicy(r.data))
      .catch(() => setPolicy(null));
  }, []);

  const loadHolidays = useCallback(() => {
    api
      .get<{ results?: { id: number; name: string; holiday_date: string; is_optional: boolean }[] } | { id: number; name: string; holiday_date: string; is_optional: boolean }[]>(
        "/hr/attendance-holidays/"
      )
      .then((r) => {
        const data = r.data;
        const rows = Array.isArray(data) ? data : data.results || [];
        setHolidays(rows);
      })
      .catch(() => setHolidays([]));
  }, []);

  useEffect(() => {
    loadCatalog();
    loadToday();
    loadPolicy();
    loadHolidays();
  }, [loadCatalog, loadToday, loadPolicy, loadHolidays]);

  const runReconcile = async (scope: "today" | "month") => {
    setReconciling(true);
    try {
      const payload =
        scope === "today"
          ? {}
          : (() => {
              const now = new Date();
              const start = new Date(now.getFullYear(), now.getMonth(), 1)
                .toISOString()
                .slice(0, 10);
              const end = new Date(now.getFullYear(), now.getMonth() + 1, 0)
                .toISOString()
                .slice(0, 10);
              return { start, end };
            })();
      const { data } = await api.post("/hr/attendance/reconcile/", payload);
      enqueueSnackbar(
        `Reconciled · leave ${data.on_leave ?? 0} · holiday ${data.holiday ?? 0} · absent ${data.absent ?? 0} · exempt ${data.exempt ?? 0}`,
        { variant: "success" }
      );
      loadToday();
      crud.load();
    } catch (e: unknown) {
      enqueueSnackbar(getApiErrorMessage(e, "Reconcile failed"), errorSnackbarOpts);
    } finally {
      setReconciling(false);
    }
  };

  const punchToday = async (empId: number, kind: "check-in" | "check-out") => {
    try {
      await api.post(`/hr/attendance/${kind}/`, { employee: empId });
      enqueueSnackbar(kind === "check-in" ? "Checked in" : "Checked out", {
        variant: "success",
      });
      loadToday();
      crud.load();
    } catch (e: unknown) {
      enqueueSnackbar(getApiErrorMessage(e, "Punch failed"), errorSnackbarOpts);
    }
  };

  const kpis = useMemo(() => {
    const rows = crud.rows;
    return {
      total: rows.length,
      present: rows.filter((r) => String(r.status) === "present").length,
      absent: rows.filter((r) => String(r.status) === "absent").length,
      device: rows.filter((r) => String(r.source) === "device").length,
    };
  }, [crud.rows]);

  const syncDevice = async (id: number, action: "test-connection" | "pull-sync") => {
    try {
      const { data } = await api.post(`/hr/attendance-devices/${id}/${action}/`);
      enqueueSnackbar(
        (data as { message?: string }).message ||
          (action === "pull-sync" ? "Pull sync queued" : "Connection OK"),
        { variant: "success" }
      );
      devicesCrud.load();
    } catch (e: unknown) {
      enqueueSnackbar(getApiErrorMessage(e, "Action failed"), errorSnackbarOpts);
    }
  };

  const devicesEnabled =
    canView(devicesModule) && (catalog?.module_enabled ?? canView(devicesModule));

  return (
    <ModuleGate module={moduleKey}>
      <Box>
        <PageHeader
          title="Attendance"
          subtitle="Daily records, biometric devices and market connectors"
        />

        <Tabs
          value={tab}
          onChange={(_, v) => {
            setTab(v);
            const names = ["today", "records", "devices", "connectors", "policy", "requests"];
            router.replace(`/hr/attendance?tab=${names[v] || "records"}`);
          }}
          sx={{ mb: 2, borderBottom: 1, borderColor: "divider" }}
          variant="scrollable"
          allowScrollButtonsMobile
        >
          <Tab label="Today" />
          <Tab label="Records" />
          <Tab label="Devices" disabled={!devicesEnabled && !canView(devicesModule)} />
          <Tab label="Connectors" />
          <Tab label="Policy" />
          <Tab label="Corrections" />
        </Tabs>

        {tab === 5 ? (
          <Stack spacing={1}>
            <Stack direction="row" spacing={1}>
              <Button
                size="small"
                variant="outlined"
                onClick={async () => {
                  const { data } = await api.get("/hr/attendance-regularizations/", {
                    params: { status: "pending" },
                  });
                  const rows = Array.isArray(data) ? data : data.results || [];
                  setCorrections(rows);
                }}
              >
                Load pending
              </Button>
            </Stack>
            {corrections.length === 0 ? (
              <Typography color="text.secondary">No correction requests loaded.</Typography>
            ) : (
              corrections.map((row) => (
                <Stack
                  key={row.id}
                  direction={{ xs: "column", sm: "row" }}
                  spacing={1}
                  alignItems={{ sm: "center" }}
                  sx={{ borderBottom: 1, borderColor: "divider", py: 1 }}
                >
                  <Box sx={{ flex: 1 }}>
                    <Typography fontWeight={700}>
                      {row.employee_code} {row.employee_name} · {row.work_date}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {row.requested_check_in || "—"} → {row.requested_check_out || "—"} · {row.reason}
                    </Typography>
                  </Box>
                  {canChange(moduleKey) ? (
                    <>
                      <Button
                        size="small"
                        variant="contained"
                        onClick={async () => {
                          await api.post(`/hr/attendance-regularizations/${row.id}/approve/`);
                          setCorrections((list) => list.filter((item) => item.id !== row.id));
                          enqueueSnackbar("Correction approved", { variant: "success" });
                        }}
                      >
                        Approve
                      </Button>
                      <Button
                        size="small"
                        color="warning"
                        onClick={async () => {
                          await api.post(`/hr/attendance-regularizations/${row.id}/reject/`);
                          setCorrections((list) => list.filter((item) => item.id !== row.id));
                          enqueueSnackbar("Correction rejected", { variant: "success" });
                        }}
                      >
                        Reject
                      </Button>
                    </>
                  ) : null}
                </Stack>
              ))
            )}
          </Stack>
        ) : null}

        {tab === 0 ? (
          <Box>
            {today ? (
              <>
                <Stack direction="row" spacing={1.5} flexWrap="wrap" useFlexGap sx={{ mb: 2 }}>
                  <Kpi label="Headcount" value={String(today.totals.headcount)} />
                  <Kpi label="Present" value={String(today.totals.present)} />
                  <Kpi label="Absent" value={String(today.totals.absent)} />
                  <Kpi label="Leave" value={String(today.totals.on_leave ?? 0)} />
                  <Kpi label="Holiday" value={String(today.totals.holiday ?? 0)} />
                  <Kpi label="Exempt" value={String(today.totals.exempt)} />
                </Stack>
                <Stack direction="row" spacing={1} sx={{ mb: 1 }} alignItems="center">
                  <Typography variant="body2" color="text.secondary" sx={{ flex: 1 }}>
                    {formatDate(today.work_date)} · live check-in / check-out board
                  </Typography>
                  {canChange(moduleKey) ? (
                    <Button
                      size="small"
                      variant="outlined"
                      disabled={reconciling}
                      onClick={() => runReconcile("today")}
                    >
                      {reconciling ? "Reconciling…" : "Reconcile today"}
                    </Button>
                  ) : null}
                </Stack>
                <CrudTable
                  title="Today"
                  subtitle="Punch board"
                  rows={today.rows.map((r) => ({ ...r, id: r.employee }))}
                  loading={false}
                  selectedIds={[]}
                  onToggleAll={() => {}}
                  onToggleOne={() => {}}
                  onRefresh={loadToday}
                  createLabel="Add"
                  canCreate={false}
                  canEdit={false}
                  canDelete={false}
                  emptyTitle="No active employees"
                  emptyHint="Add employees to see today’s board."
                  columns={[
                    {
                      key: "employee_code",
                      header: "Emp",
                      render: (r) => r.employee_code ?? "—",
                    },
                    {
                      key: "employee_name",
                      header: "Name",
                      render: (r) => r.employee_name ?? "—",
                    },
                    {
                      key: "check_in",
                      header: "In",
                      render: (r) => String(r.check_in || "—").slice(0, 8),
                    },
                    {
                      key: "check_out",
                      header: "Out",
                      render: (r) => String(r.check_out || "—").slice(0, 8),
                    },
                    {
                      key: "status",
                      header: "Status",
                      render: (r) => (
                        <Chip
                          size="small"
                          color={statusColor(String(r.status))}
                          label={
                            r.is_attendance_free ? "exempt" : String(r.status)
                          }
                          variant="outlined"
                        />
                      ),
                    },
                    {
                      key: "actions",
                      header: "",
                      render: (r) =>
                        r.is_attendance_free ? (
                          <Typography variant="caption" color="text.secondary">
                            Exempt
                          </Typography>
                        ) : (
                          <Stack direction="row" spacing={0.5}>
                            <Button
                              size="small"
                              startIcon={<LoginIcon />}
                              disabled={!canAdd(moduleKey) || !!r.check_in}
                              onClick={(e) => {
                                e.stopPropagation();
                                punchToday(r.employee, "check-in");
                              }}
                            >
                              In
                            </Button>
                            <Button
                              size="small"
                              startIcon={<LogoutIcon />}
                              disabled={!canAdd(moduleKey) || !r.check_in || !!r.check_out}
                              onClick={(e) => {
                                e.stopPropagation();
                                punchToday(r.employee, "check-out");
                              }}
                            >
                              Out
                            </Button>
                          </Stack>
                        ),
                    },
                  ]}
                />
              </>
            ) : (
              <Alert severity="info">Loading today’s board…</Alert>
            )}
          </Box>
        ) : null}

        {tab === 1 ? (
          <>
            {!crud.loading && crud.rows.length > 0 ? (
              <Stack direction="row" spacing={1.5} flexWrap="wrap" useFlexGap sx={{ mb: 2 }}>
                <Kpi label="Records" value={String(kpis.total)} />
                <Kpi label="Present" value={String(kpis.present)} />
                <Kpi label="Absent" value={String(kpis.absent)} />
                <Kpi label="From devices" value={String(kpis.device)} />
              </Stack>
            ) : null}
            <CrudTable
              title="Attendance"
              subtitle="Daily attendance, exceptions and regularization"
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
              createLabel="Add"
              canCreate={canAdd(moduleKey)}
              canEdit={canChange(moduleKey)}
              canDelete={canDelete(moduleKey)}
              emptyTitle="No attendance records"
              emptyHint="Log a daily entry or sync from a connected device."
              columns={[
                {
                  key: "employee_code",
                  header: "Emp",
                  render: (r) => r.employee_code ?? "—",
                },
                {
                  key: "employee_name",
                  header: "Name",
                  render: (r) => r.employee_name ?? "—",
                },
                {
                  key: "work_date",
                  header: "Date",
                  render: (r) => formatDate(String(r.work_date || "")),
                },
                {
                  key: "check_in",
                  header: "In",
                  render: (r) => String(r.check_in || "—").slice(0, 8),
                },
                {
                  key: "check_out",
                  header: "Out",
                  render: (r) => String(r.check_out || "—").slice(0, 8),
                },
                {
                  key: "status",
                  header: "Status",
                  render: (r) => (
                    <Chip
                      size="small"
                      color={statusColor(String(r.status))}
                      label={r.status}
                      variant="outlined"
                    />
                  ),
                },
                {
                  key: "source",
                  header: "Source",
                  render: (r) => r.source || "manual",
                },
              ]}
            />
          </>
        ) : null}

        {tab === 2 ? (
          <ModuleGate module={devicesModule}>
            {!catalog?.module_enabled ? (
              <Alert severity="warning" sx={{ mb: 2 }}>
                Attendance devices are not enabled on your subscription package. Ask the
                platform admin to enable <strong>hr.attendance_devices</strong> and assign
                connectors.
              </Alert>
            ) : (
              <Alert severity="info" sx={{ mb: 2 }}>
                Devices {catalog.devices_used}
                {catalog.max_devices != null ? ` / ${catalog.max_devices}` : ""} ·{" "}
                {catalog.connectors.filter((c) => c.entitled).length} connectors entitled
              </Alert>
            )}
            <CrudTable
              title="Attendance devices"
              subtitle="ZKTeco, Hikvision, Anviz, Suprema, eSSL and more"
              rows={devicesCrud.rows}
              loading={devicesCrud.loading}
              selectedIds={devicesCrud.selectedIds}
              onToggleAll={devicesCrud.toggleAll}
              onToggleOne={devicesCrud.toggleOne}
              onRefresh={() => {
                devicesCrud.load();
                loadCatalog();
              }}
              onCreate={devicesCrud.openCreate}
              onEdit={devicesCrud.openEdit}
              onView={devicesCrud.openView}
              onDeleteOne={devicesCrud.askDeleteOne}
              onBulkDelete={devicesCrud.askBulkDelete}
              createLabel="Add device"
              canCreate={
                canAdd(devicesModule) &&
                !!catalog?.module_enabled &&
                (catalog.max_devices == null ||
                  catalog.devices_used < (catalog.max_devices || 0))
              }
              canEdit={canChange(devicesModule)}
              canDelete={canDelete(devicesModule)}
              emptyTitle="No devices connected"
              emptyHint="Add a biometric or access terminal from an entitled connector."
              columns={[
                {
                  key: "device_id",
                  header: "Device ID",
                  render: (r) => r.device_id || "—",
                },
                {
                  key: "connector_name",
                  header: "Connector",
                  render: (r) => r.connector_name || r.connector_key,
                },
                {
                  key: "location",
                  header: "Location",
                  render: (r) => r.location || "—",
                },
                {
                  key: "connection_mode",
                  header: "Mode",
                  render: (r) => r.connection_mode?.replace(/_/g, " ") || "—",
                },
                {
                  key: "last_sync_status",
                  header: "Sync",
                  render: (r) => (
                    <Chip
                      size="small"
                      color={statusColor(String(r.last_sync_status || "idle"))}
                      label={r.last_sync_status || "idle"}
                      variant="outlined"
                    />
                  ),
                },
                {
                  key: "actions",
                  header: "",
                  render: (r) => (
                    <Stack direction="row" spacing={0.5}>
                      <Button
                        size="small"
                        startIcon={<DevicesIcon />}
                        onClick={(e) => {
                          e.stopPropagation();
                          syncDevice(r.id, "test-connection");
                        }}
                      >
                        Test
                      </Button>
                      <Button
                        size="small"
                        startIcon={<SyncIcon />}
                        onClick={(e) => {
                          e.stopPropagation();
                          syncDevice(r.id, "pull-sync");
                        }}
                      >
                        Pull
                      </Button>
                    </Stack>
                  ),
                },
              ]}
            />
            <ConfirmDialog
              open={!!devicesCrud.confirm}
              title="Delete device?"
              message="This cannot be undone."
              confirmLabel="Delete"
              loading={devicesCrud.saving}
              onClose={() => devicesCrud.setConfirm(null)}
              onConfirm={devicesCrud.runConfirmDelete}
            />
          </ModuleGate>
        ) : null}

        {tab === 3 ? (
          <Stack spacing={2}>
            <Stack
              direction={{ xs: "column", sm: "row" }}
              justifyContent="space-between"
              alignItems={{ xs: "stretch", sm: "center" }}
              spacing={1}
            >
              <Box>
                <Typography variant="subtitle1" fontWeight={700}>
                  Device connectors
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Market biometric / access adapters. Entitlement and device caps come from
                  your subscription package.
                </Typography>
              </Box>
              <Stack direction="row" spacing={1}>
                <Button size="small" onClick={loadCatalog} startIcon={<SyncIcon />}>
                  Refresh
                </Button>
                {canAdd(devicesModule) && catalog?.module_enabled ? (
                  <Button
                    size="small"
                    variant="contained"
                    startIcon={<DevicesIcon />}
                    onClick={() => router.push("/hr/attendance/devices/new")}
                  >
                    Add device
                  </Button>
                ) : null}
              </Stack>
            </Stack>

            {!catalog ? (
              <Alert severity="info">Loading connector catalog…</Alert>
            ) : (
              <>
                {!catalog.module_enabled ? (
                  <Alert severity="warning">
                    Attendance devices are not enabled on your package. Ask the platform
                    admin to enable <strong>hr.attendance_devices</strong> and assign
                    connectors.
                  </Alert>
                ) : null}

                <Stack direction="row" flexWrap="wrap" useFlexGap spacing={0}>
                  <Kpi
                    label="Catalog"
                    value={String(catalog.summary?.catalog_total ?? catalog.connectors.length)}
                  />
                  <Kpi
                    label="Entitled"
                    value={String(
                      catalog.summary?.entitled ??
                        catalog.connectors.filter((c) => c.entitled).length
                    )}
                  />
                  <Kpi
                    label="In use"
                    value={String(catalog.summary?.connectors_in_use ?? 0)}
                  />
                  <Kpi
                    label="Healthy"
                    value={String(catalog.summary?.healthy ?? 0)}
                  />
                  <Kpi
                    label="Degraded"
                    value={String(catalog.summary?.degraded ?? 0)}
                  />
                  <Kpi
                    label="Devices"
                    value={
                      catalog.max_devices != null
                        ? `${catalog.devices_used}/${catalog.max_devices}`
                        : String(catalog.devices_used)
                    }
                  />
                </Stack>

                {catalog.integration ? (
                  <Box
                    sx={{
                      p: 2,
                      border: "1px solid",
                      borderColor: "divider",
                      borderRadius: 1,
                      bgcolor: "action.hover",
                    }}
                  >
                    <Typography variant="subtitle2" fontWeight={700} gutterBottom>
                      Integration endpoints
                    </Typography>
                    <Stack spacing={1}>
                      <Stack direction="row" alignItems="center" spacing={1}>
                        <Typography variant="body2" sx={{ flex: 1, fontFamily: "monospace" }}>
                          POST {catalog.integration.webhook_path}
                        </Typography>
                        <Tooltip title="Copy path">
                          <IconButton
                            size="small"
                            onClick={() =>
                              copyText("Webhook path", catalog.integration!.webhook_path)
                            }
                          >
                            <ContentCopyIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      </Stack>
                      <Typography variant="caption" color="text.secondary">
                        Auth header: {catalog.integration.webhook_auth_header} · CSV:{" "}
                        {catalog.integration.csv_header}
                      </Typography>
                      <Stack direction="row" spacing={1}>
                        <Button
                          size="small"
                          variant="outlined"
                          startIcon={<ContentCopyIcon />}
                          onClick={() =>
                            copyText(
                              "Sample payload",
                              JSON.stringify(catalog.integration!.sample_payload, null, 2)
                            )
                          }
                        >
                          Copy sample JSON
                        </Button>
                        <Button
                          size="small"
                          variant="outlined"
                          startIcon={<ContentCopyIcon />}
                          onClick={() =>
                            copyText("CSV header", catalog.integration!.csv_header)
                          }
                        >
                          Copy CSV header
                        </Button>
                      </Stack>
                    </Stack>
                  </Box>
                ) : null}

                <Stack
                  direction={{ xs: "column", md: "row" }}
                  spacing={1.5}
                  alignItems={{ xs: "stretch", md: "center" }}
                >
                  <TextField
                    size="small"
                    placeholder="Search vendor, model, protocol…"
                    value={connQuery}
                    onChange={(e) => setConnQuery(e.target.value)}
                    sx={{ flex: 1, maxWidth: 360 }}
                  />
                  <ToggleButtonGroup
                    exclusive
                    size="small"
                    value={connFilter}
                    onChange={(_, v) => v && setConnFilter(v)}
                    sx={{ flexWrap: "wrap" }}
                  >
                    <ToggleButton value="all">All</ToggleButton>
                    <ToggleButton value="entitled">Entitled</ToggleButton>
                    <ToggleButton value="in_use">In use</ToggleButton>
                    <ToggleButton value="locked">Locked</ToggleButton>
                  </ToggleButtonGroup>
                </Stack>

                {filteredConnectors.length === 0 ? (
                  <Alert severity="info">No connectors match this filter.</Alert>
                ) : (
                  <Box
                    sx={{
                      display: "grid",
                      gap: 1.5,
                      gridTemplateColumns: {
                        xs: "1fr",
                        md: "1fr 1fr",
                      },
                    }}
                  >
                    {filteredConnectors.map((c) => {
                      const health = c.usage?.health || "unused";
                      const open = connExpanded === c.key;
                      return (
                        <Box
                          key={c.key}
                          sx={{
                            p: 2,
                            border: "1px solid",
                            borderColor:
                              health === "error"
                                ? "error.light"
                                : c.entitled
                                  ? "success.light"
                                  : "divider",
                            borderRadius: 1,
                            opacity: c.entitled ? 1 : 0.72,
                          }}
                        >
                          <Stack
                            direction="row"
                            justifyContent="space-between"
                            alignItems="flex-start"
                            spacing={1}
                          >
                            <Box sx={{ minWidth: 0 }}>
                              <Typography fontWeight={700} noWrap>
                                {c.vendor}
                              </Typography>
                              <Typography variant="body2" color="text.secondary">
                                {c.name}
                              </Typography>
                            </Box>
                            <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap>
                              <Chip
                                size="small"
                                label={c.entitled ? "Entitled" : "Locked"}
                                color={c.entitled ? "success" : "default"}
                                variant="outlined"
                              />
                              {c.usage && c.usage.devices > 0 ? (
                                <Chip
                                  size="small"
                                  label={health}
                                  color={healthColor(health)}
                                  variant="outlined"
                                />
                              ) : null}
                              {c.status && c.status !== "ga" ? (
                                <Chip size="small" label={c.status} variant="outlined" />
                              ) : null}
                            </Stack>
                          </Stack>

                          <Typography
                            variant="caption"
                            color="text.secondary"
                            display="block"
                            sx={{ mt: 1 }}
                          >
                            {(c.tier || "standard").toUpperCase()} · {c.protocol}
                            {c.category ? ` · ${c.category.replace(/_/g, " ")}` : ""}
                          </Typography>
                          <Typography variant="body2" sx={{ mt: 0.75 }}>
                            {c.models}
                          </Typography>
                          <Typography
                            variant="caption"
                            color="text.secondary"
                            display="block"
                            sx={{ mt: 0.5 }}
                          >
                            Modes: {c.modes.map((m) => m.replace(/_/g, " ")).join(" · ")}
                          </Typography>

                          {c.capabilities ? (
                            <Stack
                              direction="row"
                              spacing={0.5}
                              flexWrap="wrap"
                              useFlexGap
                              sx={{ mt: 1 }}
                            >
                              {c.capabilities.push ? (
                                <Chip size="small" label="Push" variant="outlined" />
                              ) : null}
                              {c.capabilities.pull ? (
                                <Chip size="small" label="Pull" variant="outlined" />
                              ) : null}
                              {c.capabilities.cloud ? (
                                <Chip size="small" label="Cloud" variant="outlined" />
                              ) : null}
                              {c.capabilities.csv ? (
                                <Chip size="small" label="CSV" variant="outlined" />
                              ) : null}
                              {c.capabilities.live_pull_agent ? (
                                <Chip size="small" label="Agent" variant="outlined" />
                              ) : null}
                            </Stack>
                          ) : null}

                          {c.usage && c.usage.devices > 0 ? (
                            <Typography
                              variant="caption"
                              display="block"
                              sx={{ mt: 1 }}
                              color="text.secondary"
                            >
                              {c.usage.active}/{c.usage.devices} active
                              {c.usage.errors ? ` · ${c.usage.errors} error` : ""}
                              {c.usage.last_sync_at
                                ? ` · last ${formatDate(c.usage.last_sync_at)}`
                                : ""}
                              {c.usage.device_ids?.length
                                ? ` · ${c.usage.device_ids.join(", ")}`
                                : ""}
                            </Typography>
                          ) : (
                            <Typography
                              variant="caption"
                              display="block"
                              sx={{ mt: 1 }}
                              color="text.secondary"
                            >
                              No devices on this connector yet
                            </Typography>
                          )}

                          <Typography variant="body2" sx={{ mt: 1 }}>
                            {c.docs}
                          </Typography>

                          <Stack direction="row" spacing={1} sx={{ mt: 1.5 }} flexWrap="wrap">
                            <Button
                              size="small"
                              endIcon={open ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                              onClick={() =>
                                setConnExpanded(open ? null : c.key)
                              }
                            >
                              Setup
                            </Button>
                            {c.entitled && canAdd(devicesModule) && catalog.module_enabled ? (
                              <Button
                                size="small"
                                variant="contained"
                                startIcon={<DevicesIcon />}
                                onClick={() =>
                                  router.push(
                                    `/hr/attendance/devices/new?connector=${encodeURIComponent(c.key)}`
                                  )
                                }
                              >
                                Add device
                              </Button>
                            ) : null}
                            {c.usage && c.usage.devices > 0 ? (
                              <Button
                                size="small"
                                onClick={() => {
                                  setTab(2);
                                  router.replace("/hr/attendance?tab=devices");
                                }}
                              >
                                View devices
                              </Button>
                            ) : null}
                          </Stack>

                          <Collapse in={open}>
                            <Box sx={{ mt: 1.5, pl: 1, borderLeft: "2px solid", borderColor: "divider" }}>
                              {(c.setup_steps || []).map((step, i) => (
                                <Typography key={i} variant="body2" sx={{ mb: 0.75 }}>
                                  {i + 1}. {step}
                                </Typography>
                              ))}
                              {c.sample_payload ? (
                                <Button
                                  size="small"
                                  startIcon={<ContentCopyIcon />}
                                  sx={{ mt: 0.5 }}
                                  onClick={() =>
                                    copyText(
                                      "Sample payload",
                                      JSON.stringify(c.sample_payload, null, 2)
                                    )
                                  }
                                >
                                  Copy connector payload
                                </Button>
                              ) : null}
                              {c.sample_csv_header ? (
                                <Button
                                  size="small"
                                  startIcon={<ContentCopyIcon />}
                                  sx={{ mt: 0.5, ml: 1 }}
                                  onClick={() =>
                                    copyText("CSV header", c.sample_csv_header || "")
                                  }
                                >
                                  Copy CSV columns
                                </Button>
                              ) : null}
                            </Box>
                          </Collapse>
                        </Box>
                      );
                    })}
                  </Box>
                )}
              </>
            )}
          </Stack>
        ) : null}

        {tab === 4 ? (
          <Stack spacing={3} maxWidth={640}>
            <Typography variant="body2" color="text.secondary">
              Shift rules, auto leave/holiday/absent, weekend days, and holiday calendar.
            </Typography>
            {!policy ? (
              <Alert severity="info">Loading policy…</Alert>
            ) : (
              <Stack spacing={2}>
                <TextField
                  label="Work start"
                  type="time"
                  InputLabelProps={{ shrink: true }}
                  value={String(policy.work_start || "09:00").slice(0, 5)}
                  disabled={!canChange(moduleKey)}
                  onChange={(e) =>
                    setPolicy({ ...policy, work_start: e.target.value })
                  }
                />
                <TextField
                  label="Work end"
                  type="time"
                  InputLabelProps={{ shrink: true }}
                  value={String(policy.work_end || "18:00").slice(0, 5)}
                  disabled={!canChange(moduleKey)}
                  onChange={(e) => setPolicy({ ...policy, work_end: e.target.value })}
                />
                <TextField
                  label="Late grace (minutes)"
                  type="number"
                  value={Number(policy.late_grace_minutes ?? 15)}
                  disabled={!canChange(moduleKey)}
                  onChange={(e) =>
                    setPolicy({
                      ...policy,
                      late_grace_minutes: Number(e.target.value) || 0,
                    })
                  }
                />
                <TextField
                  label="Early-leave grace (minutes)"
                  type="number"
                  value={Number(policy.early_leave_grace_minutes ?? 15)}
                  disabled={!canChange(moduleKey)}
                  onChange={(e) =>
                    setPolicy({
                      ...policy,
                      early_leave_grace_minutes: Number(e.target.value) || 0,
                    })
                  }
                />
                <TextField
                  label="Half-day minutes"
                  type="number"
                  value={Number(policy.half_day_minutes ?? 240)}
                  disabled={!canChange(moduleKey)}
                  onChange={(e) =>
                    setPolicy({
                      ...policy,
                      half_day_minutes: Number(e.target.value) || 0,
                    })
                  }
                />
                <TextField
                  label="Full-day minutes"
                  type="number"
                  value={Number(policy.full_day_minutes ?? 480)}
                  disabled={!canChange(moduleKey)}
                  onChange={(e) =>
                    setPolicy({
                      ...policy,
                      full_day_minutes: Number(e.target.value) || 0,
                    })
                  }
                />
                <TextField
                  label="Overtime after (minutes)"
                  type="number"
                  value={Number(policy.overtime_after_minutes ?? 480)}
                  disabled={!canChange(moduleKey)}
                  onChange={(e) =>
                    setPolicy({
                      ...policy,
                      overtime_after_minutes: Number(e.target.value) || 0,
                    })
                  }
                />
                <FormControlLabel
                  control={
                    <Checkbox
                      checked={!!policy.auto_apply_leave}
                      disabled={!canChange(moduleKey)}
                      onChange={(e) =>
                        setPolicy({ ...policy, auto_apply_leave: e.target.checked })
                      }
                    />
                  }
                  label="Auto-mark on_leave when leave is approved"
                />
                <FormControlLabel
                  control={
                    <Checkbox
                      checked={!!policy.auto_apply_holiday}
                      disabled={!canChange(moduleKey)}
                      onChange={(e) =>
                        setPolicy({ ...policy, auto_apply_holiday: e.target.checked })
                      }
                    />
                  }
                  label="Auto-mark holiday from calendar / weekends"
                />
                <FormControlLabel
                  control={
                    <Checkbox
                      checked={!!policy.auto_mark_absent}
                      disabled={!canChange(moduleKey)}
                      onChange={(e) =>
                        setPolicy({ ...policy, auto_mark_absent: e.target.checked })
                      }
                    />
                  }
                  label="Auto-mark absent when no punch (on reconcile)"
                />
                <Typography variant="caption" color="text.secondary">
                  Weekend days (0=Mon … 6=Sun). Empty = Sat+Sun.
                </Typography>
                <Stack direction="row" flexWrap="wrap" useFlexGap spacing={1}>
                  {["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].map((label, idx) => {
                    const days = Array.isArray(policy.weekend_days)
                      ? (policy.weekend_days as number[])
                      : [5, 6];
                    const on = days.includes(idx);
                    return (
                      <Chip
                        key={label}
                        label={label}
                        color={on ? "primary" : "default"}
                        variant={on ? "filled" : "outlined"}
                        onClick={() => {
                          if (!canChange(moduleKey)) return;
                          const set = new Set(days);
                          if (on) set.delete(idx);
                          else set.add(idx);
                          setPolicy({
                            ...policy,
                            weekend_days: Array.from(set).sort(),
                          });
                        }}
                        clickable={canChange(moduleKey)}
                      />
                    );
                  })}
                </Stack>
                {canChange(moduleKey) ? (
                  <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                    <Button
                      variant="contained"
                      disabled={policySaving}
                      onClick={async () => {
                        setPolicySaving(true);
                        try {
                          const { data } = await api.patch(
                            "/hr/attendance/policy/",
                            policy
                          );
                          setPolicy(data);
                          enqueueSnackbar("Policy saved", { variant: "success" });
                        } catch (e: unknown) {
                          enqueueSnackbar(
                            getApiErrorMessage(e, "Save failed"),
                            errorSnackbarOpts
                          );
                        } finally {
                          setPolicySaving(false);
                        }
                      }}
                    >
                      {policySaving ? "Saving…" : "Save policy"}
                    </Button>
                    <Button
                      variant="outlined"
                      disabled={reconciling}
                      onClick={() => runReconcile("today")}
                    >
                      Reconcile today
                    </Button>
                    <Button
                      variant="outlined"
                      disabled={reconciling}
                      onClick={() => runReconcile("month")}
                    >
                      Reconcile this month
                    </Button>
                  </Stack>
                ) : null}
              </Stack>
            )}

            <Box>
              <Typography variant="subtitle2" sx={{ mb: 1 }}>
                Holiday calendar
              </Typography>
              <Stack spacing={1.5} sx={{ mb: 2 }}>
                {holidays.map((h) => (
                  <Stack
                    key={h.id}
                    direction="row"
                    spacing={1}
                    alignItems="center"
                    sx={{ borderBottom: "1px solid", borderColor: "divider", pb: 1 }}
                  >
                    <Typography sx={{ flex: 1 }}>
                      {formatDate(h.holiday_date)} · {h.name}
                      {h.is_optional ? " (optional)" : ""}
                    </Typography>
                    {canDelete(moduleKey) ? (
                      <Button
                        size="small"
                        color="error"
                        onClick={async () => {
                          try {
                            await api.delete(`/hr/attendance-holidays/${h.id}/`);
                            loadHolidays();
                          } catch (e: unknown) {
                            enqueueSnackbar(
                              getApiErrorMessage(e, "Delete failed"),
                              errorSnackbarOpts
                            );
                          }
                        }}
                      >
                        Remove
                      </Button>
                    ) : null}
                  </Stack>
                ))}
                {!holidays.length ? (
                  <Typography variant="body2" color="text.secondary">
                    No holidays yet — add public holidays below.
                  </Typography>
                ) : null}
              </Stack>
              {canAdd(moduleKey) ? (
                <Stack spacing={1.5}>
                  <TextField
                    label="Holiday name"
                    value={newHoliday.name}
                    onChange={(e) =>
                      setNewHoliday({ ...newHoliday, name: e.target.value })
                    }
                  />
                  <TextField
                    label="Date"
                    type="date"
                    InputLabelProps={{ shrink: true }}
                    value={newHoliday.holiday_date}
                    onChange={(e) =>
                      setNewHoliday({ ...newHoliday, holiday_date: e.target.value })
                    }
                  />
                  <FormControlLabel
                    control={
                      <Checkbox
                        checked={newHoliday.is_optional}
                        onChange={(e) =>
                          setNewHoliday({
                            ...newHoliday,
                            is_optional: e.target.checked,
                          })
                        }
                      />
                    }
                    label="Optional (does not auto-mark)"
                  />
                  <Button
                    variant="outlined"
                    onClick={async () => {
                      if (!newHoliday.name || !newHoliday.holiday_date) {
                        enqueueSnackbar("Name and date required", {
                          variant: "warning",
                        });
                        return;
                      }
                      try {
                        await api.post("/hr/attendance-holidays/", newHoliday);
                        setNewHoliday({
                          name: "",
                          holiday_date: "",
                          is_optional: false,
                        });
                        loadHolidays();
                        enqueueSnackbar("Holiday added", { variant: "success" });
                      } catch (e: unknown) {
                        enqueueSnackbar(
                          getApiErrorMessage(e, "Could not add holiday"),
                          errorSnackbarOpts
                        );
                      }
                    }}
                  >
                    Add holiday
                  </Button>
                </Stack>
              ) : null}
            </Box>
          </Stack>
        ) : null}

        <ConfirmDialog
          open={!!crud.confirm}
          title="Confirm delete?"
          message="This cannot be undone."
          confirmLabel="Delete"
          loading={crud.saving}
          onClose={() => crud.setConfirm(null)}
          onConfirm={crud.runConfirmDelete}
        />
      </Box>
    </ModuleGate>
  );
}
