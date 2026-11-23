"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Button,
  Chip,
  CircularProgress,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";
import CheckCircleOutlinedIcon from "@mui/icons-material/CheckCircleOutlined";
import HighlightOffOutlinedIcon from "@mui/icons-material/HighlightOffOutlined";
import ModuleGate from "@/components/ModuleGate";
import PageHeader from "@/components/PageHeader";
import RowActionsMenu from "@/components/crud/RowActionsMenu";
import { useAppSelector } from "@/store/hooks";
import api from "@/lib/api";
import { errorSnackbarOpts, getApiErrorMessage } from "@/lib/apiError";
import { useSnackbar } from "notistack";

const MODULE_LABELS: Record<string, string> = {
  "finance.journals": "Finance · Journals",
  "finance.invoices": "Finance · Vendor bills",
  "finance.budgets": "Finance · Budgets",
  "sales.invoices": "Sales · Customer invoices",
  "procurement.requisitions": "Procurement · Requests",
  "procurement.orders": "Procurement · Orders",
  "hr.leaves": "HR · Leave",
  "hr.recruitment": "HR · Recruitment",
  "hr.performance": "HR · Performance",
  "hr.attendance": "HR · Attendance",
  "payroll.periods": "Payroll · Runs",
};

const ACRONYMS = new Set(["hr", "crm", "dms", "qms", "ess", "gl", "ap", "ar", "fy"]);

function presentWords(value: string) {
  return String(value || "")
    .replaceAll("_", " ")
    .replaceAll(".", " ")
    .split(/\s+/)
    .filter(Boolean)
    .map((word) => {
      const lower = word.toLowerCase();
      return ACRONYMS.has(lower) ? lower.toUpperCase() : word.charAt(0).toUpperCase() + word.slice(1).toLowerCase();
    })
    .join(" ");
}

type InboxItem = {
  module: string;
  kind: string;
  kind_label: string;
  id: number;
  label: string;
  status: string;
  amount: string;
  submitted_by: string;
  can_act: boolean;
  block_reason: string;
  href: string;
  approve_url: string;
  reject_url: string;
  open_path: string;
};

export default function ApprovalsPage() {
  const router = useRouter();
  const { enqueueSnackbar } = useSnackbar();
  const roleName =
    useAppSelector((s) => s.auth.user?.profile?.primary_role_name) ||
    useAppSelector((s) => s.auth.user?.profile?.role) ||
    "";
  const [items, setItems] = useState<InboxItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [kind, setKind] = useState("all");
  const [page, setPage] = useState(0);
  const pageSize = 20;
  const loadSeq = useRef(0);
  const itemsRef = useRef<InboxItem[]>([]);
  itemsRef.current = items;

  const load = useCallback(async () => {
    const seq = ++loadSeq.current;
    if (itemsRef.current.length === 0) setLoading(true);
    try {
      const { data } = await api.get<{ count: number; items: InboxItem[] }>("/approvals/inbox/");
      if (seq !== loadSeq.current) return;
      setItems(data.items || []);
    } catch (e: unknown) {
      if (seq !== loadSeq.current) return;
      if (itemsRef.current.length === 0) {
        enqueueSnackbar(getApiErrorMessage(e, "Failed to load approvals inbox"), errorSnackbarOpts);
      }
    } finally {
      if (seq === loadSeq.current) setLoading(false);
    }
  }, [enqueueSnackbar]);

  useEffect(() => {
    load();
  }, [load]);

  const kinds = useMemo(() => {
    const seen = new Map<string, string>();
    for (const item of items) seen.set(item.kind, item.kind_label || item.kind);
    return Array.from(seen.entries());
  }, [items]);

  const visible = kind === "all" ? items : items.filter((item) => item.kind === kind);
  const pageCount = Math.max(1, Math.ceil(visible.length / pageSize));
  const safePage = Math.min(page, pageCount - 1);
  const pageRows = visible.slice(safePage * pageSize, safePage * pageSize + pageSize);

  const act = async (item: InboxItem, action: "approve" | "reject") => {
    const key = `${item.kind}-${item.id}-${action}`;
    const previous = items;
    setBusyId(key);
    setItems((rows) => rows.filter((row) => !(row.kind === item.kind && row.id === item.id)));
    try {
      const raw = action === "approve" ? item.approve_url : item.reject_url;
      const path = raw.replace(/^\/?api\//, "");
      await api.post(path);
      enqueueSnackbar(`${action === "approve" ? "Approved" : "Rejected"}: ${item.label}`, {
        variant: "success",
      });
      void load();
    } catch (e: unknown) {
      const status = (e as { response?: { status?: number } }).response?.status;
      const message = getApiErrorMessage(e, `${action === "approve" ? "Approve" : "Reject"} failed`);
      const missing =
        status === 404 || /no longer waiting|not found|http 404/i.test(message);
      if (!missing) setItems(previous);
      enqueueSnackbar(
        missing
          ? `${item.label} is no longer waiting for approval. It may already have been approved, rejected, or removed.`
          : action === "reject" && /cannot approve/i.test(message)
            ? "Reject was blocked by the approval rule. Ask another approver, or refresh and try Reject again."
            : message,
        errorSnackbarOpts
      );
      if (missing) void load();
    } finally {
      setBusyId(null);
    }
  };

  const moduleLabel = (module: string) => MODULE_LABELS[module] || presentWords(module) || "General";
  const typeLabel = (item: InboxItem) => presentWords(item.kind_label || item.kind);

  const roleLabel = roleName ? roleName.replaceAll("_", " ") : "your role";

  return (
    <ModuleGate module="approvals">
      <PageHeader
        title="Approvals"
        subtitle={`Waiting for ${roleLabel}. Other roles' queues stay hidden.`}
        moduleKey="approvals"
      />
      <Stack direction="row" spacing={1} sx={{ mb: 2, flexWrap: "wrap" }} useFlexGap>
        <Chip
          label={`All (${items.length})`}
          color={kind === "all" ? "primary" : "default"}
          variant={kind === "all" ? "filled" : "outlined"}
          onClick={() => {
            setKind("all");
            setPage(0);
          }}
        />
        {kinds.map(([code, label]) => (
          <Chip
            key={code}
            label={`${label} (${items.filter((item) => item.kind === code).length})`}
            color={kind === code ? "primary" : "default"}
            variant={kind === code ? "filled" : "outlined"}
            onClick={() => {
              setKind(code);
              setPage(0);
            }}
          />
        ))}
        <Button sx={{ ml: "auto" }} variant="outlined" onClick={load} disabled={loading}>
          Refresh
        </Button>
      </Stack>
      <Paper variant="outlined">
        {loading ? (
          <Stack alignItems="center" p={5}>
            <CircularProgress />
          </Stack>
        ) : (
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell sx={{ fontWeight: 700 }}>Type</TableCell>
                <TableCell sx={{ fontWeight: 700 }}>Module</TableCell>
                <TableCell sx={{ fontWeight: 700 }}>Item</TableCell>
                <TableCell sx={{ fontWeight: 700 }}>Amount</TableCell>
                <TableCell sx={{ fontWeight: 700 }}>Submitted by</TableCell>
                <TableCell sx={{ fontWeight: 700 }}>Status</TableCell>
                <TableCell align="right" sx={{ fontWeight: 700 }}>
                  Actions
                </TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {visible.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7}>
                    <Typography color="text.secondary" py={3} textAlign="center">
                      Nothing is waiting for {roleLabel}.
                    </Typography>
                  </TableCell>
                </TableRow>
              ) : (
                pageRows.map((item) => (
                  <TableRow key={`${item.kind}-${item.id}`} hover>
                    <TableCell sx={{ whiteSpace: "nowrap" }}>
                      <Typography variant="body2" fontWeight={600}>
                        {typeLabel(item)}
                      </Typography>
                    </TableCell>
                    <TableCell sx={{ whiteSpace: "nowrap" }}>
                      <Chip size="small" variant="outlined" label={moduleLabel(item.module)} />
                    </TableCell>
                    <TableCell>
                      {item.open_path ? (
                        <Link href={item.open_path}>{item.label}</Link>
                      ) : (
                        item.label
                      )}
                    </TableCell>
                    <TableCell>{item.amount || "—"}</TableCell>
                    <TableCell>{item.submitted_by || "—"}</TableCell>
                    <TableCell>
                      <Chip size="small" label={item.status} variant="outlined" />
                    </TableCell>
                    <TableCell align="right">
                      <Stack spacing={0.5} alignItems="flex-end">
                        <RowActionsMenu
                          onView={
                            item.open_path ? () => router.push(item.open_path) : undefined
                          }
                          extraActions={[
                            {
                              key: "approve",
                              label:
                                busyId === `${item.kind}-${item.id}-approve`
                                  ? "Approving…"
                                  : "Approve",
                              icon: <CheckCircleOutlinedIcon fontSize="small" />,
                              disabled:
                                !item.can_act ||
                                Boolean(busyId?.startsWith(`${item.kind}-${item.id}-`)),
                              onClick: () => void act(item, "approve"),
                            },
                            {
                              key: "reject",
                              label: busyId === `${item.kind}-${item.id}-reject` ? "Rejecting…" : "Reject",
                              icon: <HighlightOffOutlinedIcon fontSize="small" />,
                              danger: true,
                              dividerBefore: true,
                              disabled:
                                !item.can_act ||
                                Boolean(busyId?.startsWith(`${item.kind}-${item.id}-`)),
                              onClick: () => void act(item, "reject"),
                            },
                          ]}
                        />
                        {item.block_reason ? (
                          <Typography variant="caption" color="text.secondary" sx={{ maxWidth: 220 }}>
                            {item.block_reason}
                          </Typography>
                        ) : null}
                      </Stack>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        )}
      </Paper>
      {visible.length > 0 ? (
        <Stack direction="row" spacing={1} alignItems="center" justifyContent="flex-end" sx={{ mt: 1 }}>
          <Typography variant="body2" color="text.secondary">
            {pageRows.length} out of {visible.length} items showing on this page
          </Typography>
          {visible.length > pageSize ? (
            <>
              <Button size="small" disabled={safePage === 0} onClick={() => setPage(safePage - 1)}>
                Previous
              </Button>
              <Button size="small" disabled={safePage >= pageCount - 1} onClick={() => setPage(safePage + 1)}>
                Next
              </Button>
            </>
          ) : null}
        </Stack>
      ) : null}
    </ModuleGate>
  );
}
