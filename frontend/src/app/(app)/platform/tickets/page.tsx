"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  MenuItem,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import DoneAllIcon from "@mui/icons-material/DoneAll";
import CrudTable from "@/components/crud/CrudTable";
import ConfirmDialog from "@/components/crud/ConfirmDialog";
import PlatformGate from "@/components/PlatformGate";
import { useCrudController } from "@/hooks/useCrudController";
import api from "@/lib/api";
import { useSnackbar } from "notistack";

type Msg = {
  id: number;
  body: string;
  is_internal: boolean;
  is_from_platform: boolean;
  author_name?: string;
  created_at: string;
};

type Ticket = {
  id: number;
  ticket_no: string;
  subject: string;
  category: string;
  priority: string;
  status: string;
  organization_name?: string;
  organization_code?: string;
  messages?: Msg[];
};

export default function PlatformTicketsPage() {
  const crud = useCrudController<Ticket>("/platform/tickets/", "Ticket");
  const { enqueueSnackbar } = useSnackbar();
  const [selected, setSelected] = useState<Ticket | null>(null);
  const [reply, setReply] = useState("");
  const [internal, setInternal] = useState(false);
  const [busy, setBusy] = useState(false);
  const [confirmClose, setConfirmClose] = useState<Ticket | null>(null);

  const refreshSelected = useCallback(async () => {
    await crud.load();
  }, [crud]);

  useEffect(() => {
    if (!selected) return;
    const fresh = crud.rows.find((t) => t.id === selected.id);
    if (fresh) setSelected(fresh);
  }, [crud.rows, selected?.id]);

  const send = async () => {
    if (!selected || !reply.trim()) return;
    setBusy(true);
    try {
      await api.post(`/platform/tickets/${selected.id}/reply/`, {
        body: reply,
        is_internal: internal,
      });
      setReply("");
      setInternal(false);
      enqueueSnackbar("Reply sent", { variant: "success" });
      await refreshSelected();
    } catch {
      enqueueSnackbar("Reply failed", { variant: "error" });
    } finally {
      setBusy(false);
    }
  };

  const setStatus = async (status: string) => {
    if (!selected) return;
    try {
      await api.patch(`/platform/tickets/${selected.id}/`, { status });
      await refreshSelected();
    } catch {
      enqueueSnackbar("Update failed", { variant: "error" });
    }
  };

  const runClose = async () => {
    if (!confirmClose) return;
    setBusy(true);
    try {
      await api.patch(`/platform/tickets/${confirmClose.id}/`, { status: "closed" });
      enqueueSnackbar("Ticket closed", { variant: "success" });
      setConfirmClose(null);
      if (selected?.id === confirmClose.id) setSelected(null);
      crud.load();
    } catch {
      enqueueSnackbar("Close failed", { variant: "error" });
    } finally {
      setBusy(false);
    }
  };

  return (
    <PlatformGate capability="tickets">
      <Stack spacing={2}>
        <CrudTable
          title="Support tickets"
          subtitle="Platform ↔ tenant helpdesk · three-dot view / close / delete · bulk delete"
          rows={crud.rows}
          loading={crud.loading}
          selectedIds={crud.selectedIds}
          onToggleAll={crud.toggleAll}
          onToggleOne={crud.toggleOne}
          onRefresh={crud.load}
          onView={(row) => setSelected(row)}
          onDeleteOne={crud.askDeleteOne}
          onBulkDelete={crud.askBulkDelete}
          canCreate={false}
          canEdit={false}
          canDelete
          getRowActions={(row) =>
            row.status !== "closed"
              ? [
                  {
                    key: "close",
                    label: "Close ticket",
                    icon: <DoneAllIcon fontSize="small" />,
                    onClick: () => setConfirmClose(row),
                    dividerBefore: true,
                  },
                ]
              : []
          }
          columns={[
            { key: "no", header: "Ticket", render: (t) => t.ticket_no },
            { key: "subject", header: "Subject", render: (t) => t.subject },
            {
              key: "org",
              header: "Tenant",
              render: (t) => `${t.organization_name || ""} (${t.organization_code || ""})`,
            },
            { key: "cat", header: "Category", render: (t) => t.category },
            { key: "pri", header: "Priority", render: (t) => t.priority },
            {
              key: "status",
              header: "Status",
              render: (t) => <Chip size="small" label={t.status} />,
            },
          ]}
        />

        {selected ? (
          <Card variant="outlined">
            <CardContent>
              <Stack spacing={2}>
                <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
                  <Typography variant="h6">{selected.subject}</Typography>
                  <Chip size="small" label={selected.ticket_no} />
                  <Chip size="small" label={selected.category} variant="outlined" />
                </Stack>
                <TextField
                  select
                  size="small"
                  label="Status"
                  value={selected.status}
                  onChange={(e) => setStatus(e.target.value)}
                  sx={{ maxWidth: 220 }}
                >
                  {["open", "in_progress", "waiting", "resolved", "closed"].map((s) => (
                    <MenuItem key={s} value={s}>
                      {s}
                    </MenuItem>
                  ))}
                </TextField>
                <Stack spacing={1.5} sx={{ maxHeight: 320, overflow: "auto" }}>
                  {(selected.messages || []).map((m) => (
                    <Box
                      key={m.id}
                      sx={{
                        p: 1.25,
                        borderRadius: 1,
                        bgcolor: m.is_internal
                          ? "warning.light"
                          : m.is_from_platform
                            ? "action.hover"
                            : "background.default",
                        border: "1px solid",
                        borderColor: "divider",
                      }}
                    >
                      <Typography variant="caption" color="text.secondary">
                        {m.author_name} · {new Date(m.created_at).toLocaleString()}
                        {m.is_internal ? " · internal" : ""}
                      </Typography>
                      <Typography whiteSpace="pre-wrap">{m.body}</Typography>
                    </Box>
                  ))}
                </Stack>
                <TextField
                  label="Reply"
                  multiline
                  minRows={3}
                  value={reply}
                  onChange={(e) => setReply(e.target.value)}
                  fullWidth
                />
                <Stack direction="row" spacing={1}>
                  <Button
                    variant="contained"
                    onClick={send}
                    disabled={busy || !reply.trim()}
                  >
                    Send reply
                  </Button>
                  <Button
                    variant={internal ? "contained" : "outlined"}
                    color="warning"
                    onClick={() => setInternal(!internal)}
                  >
                    {internal ? "Internal note ON" : "Internal note"}
                  </Button>
                  <Button onClick={() => setSelected(null)}>Close panel</Button>
                </Stack>
              </Stack>
            </CardContent>
          </Card>
        ) : null}
      </Stack>

      <ConfirmDialog
        open={!!crud.confirm}
        title={
          crud.confirm?.type === "bulk" ? "Delete selected tickets?" : "Delete ticket?"
        }
        message={
          crud.confirm?.type === "bulk"
            ? `Permanently delete ${crud.selectedIds.length} ticket(s) and their messages?`
            : `Delete ticket “${crud.confirm?.row?.ticket_no}”?`
        }
        confirmLabel="Delete"
        loading={crud.saving}
        onClose={() => crud.setConfirm(null)}
        onConfirm={crud.runConfirmDelete}
      />

      <ConfirmDialog
        open={!!confirmClose}
        title="Close ticket?"
        message={`Close “${confirmClose?.ticket_no} — ${confirmClose?.subject}”?`}
        confirmLabel="Close ticket"
        danger={false}
        loading={busy}
        onClose={() => setConfirmClose(null)}
        onConfirm={runClose}
      />
    </PlatformGate>
  );
}
