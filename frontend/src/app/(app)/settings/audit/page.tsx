"use client";

import { useCallback, useEffect, useState } from "react";
import { Box, Button, Chip, MenuItem, TextField, Typography } from "@mui/material";
import CrudTable from "@/components/crud/CrudTable";
import DateTextField from "@/components/DateTextField";
import ModuleGate from "@/components/ModuleGate";
import api from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import { useRouter } from "next/navigation";
import { useSnackbar } from "notistack";

type Row = {
  id: number;
  created_at?: string;
  who: string;
  role?: string;
  event: string;
  area: string;
  outcome: string;
  change?: string;
  href?: string;
};

type Page = {
  count?: number;
  next?: string | null;
  previous?: string | null;
  denied?: number;
  results?: Row[];
};

const moduleKey = "settings.audit";
const basePath = "/settings/audit";

const ACTIVITY = [
  { value: "", label: "All activity" },
  { value: "created", label: "Created" },
  { value: "updated", label: "Updated" },
  { value: "removed", label: "Removed" },
  { value: "submitted", label: "Submitted" },
  { value: "approved", label: "Approved" },
  { value: "rejected", label: "Rejected" },
  { value: "posted", label: "Posted" },
  { value: "denied", label: "Not allowed" },
];

const AREAS = [
  { value: "", label: "All areas" },
  { value: "finance", label: "Finance" },
  { value: "sales", label: "Sales" },
  { value: "procurement", label: "Procurement" },
  { value: "inventory", label: "Inventory" },
  { value: "hr", label: "HR" },
  { value: "payroll", label: "Payroll" },
  { value: "crm", label: "CRM" },
  { value: "projects", label: "Projects" },
  { value: "documents", label: "Documents" },
  { value: "manufacturing", label: "Manufacturing" },
  { value: "quality", label: "Quality" },
  { value: "service", label: "Service" },
  { value: "contracts", label: "Contracts" },
  { value: "settings", label: "Settings" },
];

function Outcome({ value }: { value?: string }) {
  const denied = value === "Denied";
  return (
    <Chip
      size="small"
      label={value || "Completed"}
      color={denied ? "warning" : "success"}
      variant="outlined"
    />
  );
}

export default function Page() {
  const router = useRouter();
  const { enqueueSnackbar } = useSnackbar();
  const [rows, setRows] = useState<Row[]>([]);
  const [loading, setLoading] = useState(true);
  const [q, setQ] = useState("");
  const [kind, setKind] = useState("");
  const [area, setArea] = useState("");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [page, setPage] = useState(1);
  const [count, setCount] = useState(0);
  const [denied, setDenied] = useState(0);
  const [hasNext, setHasNext] = useState(false);
  const [hasPrev, setHasPrev] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    const params: Record<string, string> = { page: String(page) };
    if (q.trim()) params.search = q.trim();
    if (kind === "denied") params.outcome = "denied";
    else if (kind) params.kind = kind;
    if (area) params.area = area;
    if (from) params.from = from;
    if (to) params.to = to;
    api
      .get<Page | Row[]>("/settings/audit/", { params })
      .then((r) => {
        const data = r.data;
        if (Array.isArray(data)) {
          setRows(data);
          setCount(data.length);
          setDenied(data.filter((row) => row.outcome === "Denied").length);
          setHasNext(false);
          setHasPrev(false);
          return;
        }
        setRows(data.results || []);
        setCount(data.count || 0);
        setDenied(data.denied || 0);
        setHasNext(Boolean(data.next));
        setHasPrev(Boolean(data.previous));
      })
      .catch(() => enqueueSnackbar("Unable to load the audit trail", { variant: "error" }))
      .finally(() => setLoading(false));
  }, [enqueueSnackbar, q, kind, area, from, to, page]);

  useEffect(() => {
    const t = setTimeout(load, q ? 250 : 0);
    return () => clearTimeout(t);
  }, [load, q]);

  return (
    <ModuleGate module={moduleKey}>
      <CrudTable
        title="Audit trail"
        subtitle="Who changed a business record, and whether the system allowed it"
        rows={rows}
        loading={loading}
        selectedIds={[]}
        onToggleAll={() => undefined}
        onToggleOne={() => undefined}
        onRefresh={load}
        onView={(row) => router.push(`${basePath}/${row.id}`)}
        onCreate={() => undefined}
        onEdit={() => undefined}
        onDeleteOne={() => undefined}
        onBulkDelete={() => undefined}
        canCreate={false}
        canEdit={false}
        canDelete={false}
        emptyTitle="No matching activity"
        emptyHint="Try another area, person, or date."
        toolbarExtra={
          <>
            <TextField
              size="small"
              label="Search"
              placeholder="Person or record"
              value={q}
              onChange={(e) => {
                setPage(1);
                setQ(e.target.value);
              }}
            />
            <TextField
              size="small"
              select
              label="Activity"
              value={kind}
              onChange={(e) => {
                setPage(1);
                setKind(e.target.value);
              }}
            >
              {ACTIVITY.map((o) => (
                <MenuItem key={o.value || "all"} value={o.value}>
                  {o.label}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              size="small"
              select
              label="Area"
              value={area}
              onChange={(e) => {
                setPage(1);
                setArea(e.target.value);
              }}
            >
              {AREAS.map((o) => (
                <MenuItem key={o.value || "all-areas"} value={o.value}>
                  {o.label}
                </MenuItem>
              ))}
            </TextField>
            <DateTextField
              size="small"
              label="From"
              showFormatHint={false}
              value={from}
              onChange={(e) => {
                setPage(1);
                setFrom(e.target.value);
              }}
            />
            <DateTextField
              size="small"
              label="To"
              showFormatHint={false}
              value={to}
              onChange={(e) => {
                setPage(1);
                setTo(e.target.value);
              }}
            />
          </>
        }
        columns={[
          {
            key: "created_at",
            header: "When",
            width: 170,
            render: (r) => formatDateTime(r.created_at),
          },
          {
            key: "who",
            header: "Who",
            width: 200,
            render: (r) => (
              <Box>
                <Typography variant="body2">{r.who || "System"}</Typography>
                {r.role ? (
                  <Typography variant="caption" color="text.secondary">
                    {r.role}
                  </Typography>
                ) : null}
              </Box>
            ),
          },
          {
            key: "event",
            header: "What happened",
            render: (r) => (
              <Box>
                <Typography variant="body2">{r.event}</Typography>
                {r.change ? (
                  <Typography variant="caption" color="text.secondary">
                    {r.change}
                  </Typography>
                ) : null}
              </Box>
            ),
          },
          { key: "area", header: "Area", width: 220, render: (r) => r.area || "—" },
          {
            key: "outcome",
            header: "Outcome",
            width: 130,
            render: (r) => <Outcome value={r.outcome} />,
          },
        ]}
      />
      <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mt: -1 }}>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          <Typography variant="body2" color="text.secondary">
            {count} events
          </Typography>
          {denied > 0 ? (
            <Button
              size="small"
              color="warning"
              onClick={() => {
                setPage(1);
                setKind("denied");
              }}
            >
              {denied} not allowed
            </Button>
          ) : null}
        </Box>
        <Box>
          <Button size="small" disabled={!hasPrev || loading} onClick={() => setPage((p) => Math.max(1, p - 1))}>
            Newer
          </Button>
          <Button size="small" disabled={!hasNext || loading} onClick={() => setPage((p) => p + 1)}>
            Older
          </Button>
        </Box>
      </Box>
    </ModuleGate>
  );
}
