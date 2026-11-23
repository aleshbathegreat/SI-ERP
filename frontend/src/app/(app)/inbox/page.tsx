"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Box, Button, Chip, Paper, Stack, Typography } from "@mui/material";
import api from "@/lib/api";
import { listResource } from "@/lib/crudApi";

type Message = {
  id: number;
  title: string;
  body: string;
  href: string;
  kind: string;
  read_at: string | null;
  created_at: string;
};

export default function InboxPage() {
  const [rows, setRows] = useState<Message[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setRows(await listResource<Message>("/inbox/"));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const markRead = async (row: Message) => {
    await api.post(`/inbox/${row.id}/read/`);
    load();
  };

  return (
    <Stack spacing={2}>
      <Box>
        <Typography variant="h5" fontWeight={700}>
          Notifications
        </Typography>
        <Typography color="text.secondary" variant="body2">
          Notices from workflows, comments, and assigned tasks.
        </Typography>
      </Box>
      {loading ? <Typography color="text.secondary">Loading…</Typography> : null}
      {!loading && rows.length === 0 ? (
        <Typography color="text.secondary">No notifications yet.</Typography>
      ) : null}
      {rows.map((row) => (
        <Paper key={row.id} variant="outlined" sx={{ p: 2 }}>
          <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 0.5 }}>
            <Typography fontWeight={row.read_at ? 500 : 700} sx={{ flex: 1 }}>
              {row.title}
            </Typography>
            <Chip size="small" label={row.kind} variant="outlined" />
            {row.read_at ? null : (
              <Button size="small" onClick={() => markRead(row)}>
                Mark read
              </Button>
            )}
          </Stack>
          <Typography variant="body2" color="text.secondary">
            {row.body}
          </Typography>
          <Stack direction="row" spacing={2} sx={{ mt: 1 }}>
            <Typography variant="caption" color="text.secondary">
              {new Date(row.created_at).toLocaleString()}
            </Typography>
            {row.href ? (
              <Typography variant="caption" component={Link} href={row.href}>
                Open record
              </Typography>
            ) : null}
          </Stack>
        </Paper>
      ))}
    </Stack>
  );
}
