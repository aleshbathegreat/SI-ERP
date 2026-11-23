"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Alert, Box, Button, Chip, CircularProgress, Stack, Typography } from "@mui/material";
import DraftsOutlinedIcon from "@mui/icons-material/DraftsOutlined";
import FlagOutlinedIcon from "@mui/icons-material/FlagOutlined";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import EssSection, { EssPanel } from "@/components/ess/EssSection";
import RowActionsMenu from "@/components/crud/RowActionsMenu";
import api from "@/lib/api";
import { getApiErrorMessage } from "@/lib/apiError";

type Notice = {
  id: number;
  title: string;
  body: string;
  href: string;
  kind: string;
  read_at: string | null;
  created_at: string;
};

type Filter = "all" | "unread" | "read" | "flagged" | string;

function kindLabel(kind: string) {
  const text = (kind || "notice").replaceAll("_", " ");
  return text.charAt(0).toUpperCase() + text.slice(1);
}

export default function EssNotificationsPage() {
  const router = useRouter();
  const [rows, setRows] = useState<Notice[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");
  const [filter, setFilter] = useState<Filter>("all");
  const [flags, setFlags] = useState<number[]>([]);

  const load = async () => {
    setLoading(true);
    setErr("");
    try {
      const { data } = await api.get<Notice[] | { results: Notice[] }>("/inbox/");
      setRows(Array.isArray(data) ? data : data.results || []);
    } catch (e: unknown) {
      setErr(getApiErrorMessage(e, "Could not load notifications"));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    try {
      const saved = JSON.parse(localStorage.getItem("sierp-inbox-flags") || "[]");
      if (Array.isArray(saved)) setFlags(saved.map((id) => Number(id)).filter(Boolean));
    } catch {
      setFlags([]);
    }
  }, []);

  const persistFlags = (next: number[]) => {
    setFlags(next);
    localStorage.setItem("sierp-inbox-flags", JSON.stringify(next));
  };

  const toggleFlag = (id: number) => {
    persistFlags(flags.includes(id) ? flags.filter((item) => item !== id) : [...flags, id]);
  };

  const dismiss = async (row: Notice) => {
    try {
      await api.post(`/inbox/${row.id}/dismiss/`);
      setRows((current) => current.filter((item) => item.id !== row.id));
      persistFlags(flags.filter((id) => id !== row.id));
    } catch (e: unknown) {
      setErr(getApiErrorMessage(e, "Could not delete that notification"));
    }
  };

  const markRead = async (row: Notice) => {
    try {
      await api.post(`/inbox/${row.id}/read/`);
      setRows((current) =>
        current.map((item) => (item.id === row.id ? { ...item, read_at: new Date().toISOString() } : item))
      );
    } catch (e: unknown) {
      setErr(getApiErrorMessage(e, "Could not mark that notification read"));
    }
  };

  const markAll = async () => {
    try {
      await Promise.all(rows.filter((row) => !row.read_at).map((row) => api.post(`/inbox/${row.id}/read/`)));
      const stamp = new Date().toISOString();
      setRows((current) => current.map((row) => (row.read_at ? row : { ...row, read_at: stamp })));
    } catch (e: unknown) {
      setErr(getApiErrorMessage(e, "Could not mark notifications read"));
    }
  };

  const unread = rows.filter((row) => !row.read_at).length;
  const read = rows.length - unread;
  const flagged = rows.filter((row) => flags.includes(row.id)).length;
  const kinds = useMemo(() => {
    const seen = new Map<string, number>();
    for (const row of rows) {
      const key = row.kind || "notice";
      seen.set(key, (seen.get(key) || 0) + 1);
    }
    return [...seen.entries()];
  }, [rows]);

  const shown = rows.filter((row) => {
    if (filter === "unread") return !row.read_at;
    if (filter === "read") return Boolean(row.read_at);
    if (filter === "flagged") return flags.includes(row.id);
    if (filter !== "all") return (row.kind || "notice") === filter;
    return true;
  });

  const chip = (key: Filter, label: string) => (
    <Chip
      key={key}
      label={label}
      color={filter === key ? "primary" : "default"}
      variant={filter === key ? "filled" : "outlined"}
      onClick={() => setFilter(key)}
    />
  );

  return (
    <EssSection
      title="Notifications"
      subtitle="Request updates, assignments, and reminders."
      action={unread ? <Button onClick={markAll}>Mark all read</Button> : null}
    >
      <Stack direction="row" spacing={1} sx={{ mb: 2, flexWrap: "wrap" }} useFlexGap>
        {chip("all", `All (${rows.length})`)}
        {chip("unread", `Unread (${unread})`)}
        {chip("read", `Read (${read})`)}
        {chip("flagged", `Flagged (${flagged})`)}
        {kinds.map(([code, count]) => chip(code, `${kindLabel(code)} (${count})`))}
      </Stack>
      {err ? <Alert severity="error" sx={{ mb: 2 }}>{err}</Alert> : null}
      <EssPanel>
        {loading ? (
          <Box sx={{ display: "grid", placeItems: "center", minHeight: 160 }}>
            <CircularProgress size={28} />
          </Box>
        ) : shown.length === 0 ? (
          <Typography color="text.secondary">
            {filter === "all" ? "No notifications yet." : "Nothing matches this filter."}
          </Typography>
        ) : (
          shown.map((row) => {
            const flaggedRow = flags.includes(row.id);
            return (
              <Box key={row.id} sx={{ py: 1.25, borderBottom: "1px solid", borderColor: "divider" }}>
                <Stack direction="row" spacing={1} alignItems="center">
                  <Typography fontWeight={row.read_at ? 500 : 700} sx={{ flex: 1 }}>{row.title}</Typography>
                  <Chip size="small" label={kindLabel(row.kind)} variant="outlined" />
                  {row.read_at ? null : <Chip size="small" color="primary" label="Unread" />}
                  {flaggedRow ? <Chip size="small" color="warning" label="Flagged" /> : null}
                  <RowActionsMenu
                    extraActions={[
                      ...(row.href
                        ? [{
                            key: "open",
                            label: "Open",
                            icon: <OpenInNewIcon fontSize="small" />,
                            onClick: () => router.push(row.href),
                          }]
                        : []),
                      ...(!row.read_at
                        ? [{
                            key: "read",
                            label: "Mark read",
                            icon: <DraftsOutlinedIcon fontSize="small" />,
                            onClick: () => { void markRead(row); },
                          }]
                        : []),
                      {
                        key: "flag",
                        label: flaggedRow ? "Unflag" : "Flag",
                        icon: <FlagOutlinedIcon fontSize="small" />,
                        onClick: () => toggleFlag(row.id),
                      },
                    ]}
                    onDelete={() => { void dismiss(row); }}
                  />
                </Stack>
                {row.body ? (
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>{row.body}</Typography>
                ) : null}
                <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: "block" }}>
                  {new Date(row.created_at).toLocaleString()}
                </Typography>
              </Box>
            );
          })
        )}
      </EssPanel>
    </EssSection>
  );
}
