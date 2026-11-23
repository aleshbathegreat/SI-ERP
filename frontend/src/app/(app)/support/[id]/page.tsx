"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  Box,
  Button,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { useSnackbar } from "notistack";
import FormPageShell from "@/components/crud/FormPageShell";
import api from "@/lib/api";
import { getResource } from "@/lib/crudApi";

type Msg = {
  id: number;
  body: string;
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
  messages?: Msg[];
};

const basePath = "/support";

export default function TicketDetailPage() {
  const params = useParams();
  const id = String(params.id);
  const router = useRouter();
  const { enqueueSnackbar } = useSnackbar();
  const [ticket, setTicket] = useState<Ticket | null>(null);
  const [loading, setLoading] = useState(true);
  const [reply, setReply] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    getResource<Ticket>("/support/tickets/", id)
      .then(setTicket)
      .catch(() => {
        enqueueSnackbar("Failed to load ticket", { variant: "error" });
        router.replace(basePath);
      })
      .finally(() => setLoading(false));
  }, [id, enqueueSnackbar, router]);

  useEffect(() => {
    load();
  }, [load]);

  const send = async () => {
    if (!ticket || !reply.trim()) return;
    setBusy(true);
    try {
      await api.post(`/support/tickets/${ticket.id}/reply/`, { body: reply });
      setReply("");
      enqueueSnackbar("Reply sent", { variant: "success" });
      load();
    } catch {
      enqueueSnackbar("Reply failed", { variant: "error" });
    } finally {
      setBusy(false);
    }
  };

  return (
    <FormPageShell
      title={ticket ? `${ticket.ticket_no} · ${ticket.subject}` : "Ticket"}
      subtitle={
        ticket
          ? `${ticket.category} · ${ticket.priority} · ${ticket.status}`
          : undefined
      }
      backHref={basePath}
      mode="view"
      loading={loading}
      maxWidth={880}
    >
      {ticket ? (
        <>
          <Stack spacing={1} sx={{ maxHeight: 420, overflow: "auto" }}>
            {(ticket.messages || []).map((m) => (
              <Box
                key={m.id}
                sx={{
                  p: 1.25,
                  borderRadius: 1,
                  bgcolor: m.is_from_platform ? "action.hover" : "background.default",
                  border: "1px solid",
                  borderColor: "divider",
                }}
              >
                <Typography variant="caption" color="text.secondary">
                  {m.author_name} · {new Date(m.created_at).toLocaleString()}
                  {m.is_from_platform ? " · platform" : ""}
                </Typography>
                <Typography whiteSpace="pre-wrap">{m.body}</Typography>
              </Box>
            ))}
          </Stack>
          {ticket.status !== "closed" ? (
            <>
              <TextField
                label="Reply"
                multiline
                minRows={3}
                value={reply}
                onChange={(e) => setReply(e.target.value)}
                fullWidth
              />
              <Button
                variant="contained"
                onClick={send}
                disabled={busy || !reply.trim()}
                sx={{ alignSelf: "flex-start" }}
              >
                Send reply
              </Button>
            </>
          ) : null}
        </>
      ) : null}
    </FormPageShell>
  );
}
