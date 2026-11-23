"use client";

import { Suspense, useCallback, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import {
  Button,
  Chip,
  MenuItem,
  Paper,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { useSnackbar } from "notistack";
import PageHeader from "@/components/PageHeader";
import api from "@/lib/api";
import { errorSnackbarOpts, getApiErrorMessage } from "@/lib/apiError";
import { unwrapList } from "@/lib/crudApi";

type MailboxProfile = {
  id: number;
  name: string;
  email: string;
  inbound: string;
  owner_label?: string;
};

type MailRow = {
  id: number;
  direction: string;
  status: string;
  subject: string;
  body: string;
  from_email: string;
  to_emails: string;
  error: string;
  occurred_at: string | null;
};

function directionLabel(row: MailRow) {
  if (row.status === "failed") return "Failed";
  if (row.direction === "in") return "Received";
  return "Sent";
}

function MailboxScreen() {
  const params = useSearchParams();
  const { enqueueSnackbar } = useSnackbar();
  const [profiles, setProfiles] = useState<MailboxProfile[]>([]);
  const [profileId, setProfileId] = useState("");
  const [rows, setRows] = useState<MailRow[]>([]);
  const [to, setTo] = useState(params.get("to") || "");
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [lead, setLead] = useState(params.get("lead") || "");
  const [opportunity, setOpportunity] = useState(params.get("opportunity") || "");
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [checking, setChecking] = useState(false);

  const loadMessages = useCallback(async (id: string) => {
    if (!id) {
      setRows([]);
      return;
    }
    const { data } = await api.get<MailRow[] | { results: MailRow[] }>("/settings/mail-messages/", {
      params: { profile: id },
    });
    setRows(unwrapList(data));
  }, []);

  useEffect(() => {
    api
      .get<MailboxProfile[] | { results: MailboxProfile[] }>("/settings/mail-messages/profiles/")
      .then((res) => {
        const list = unwrapList(res.data);
        setProfiles(list);
        setProfileId((current) => current || (list[0] ? String(list[0].id) : ""));
      })
      .catch((error) => {
        enqueueSnackbar(getApiErrorMessage(error, "Could not load mailboxes"), errorSnackbarOpts);
      })
      .finally(() => setLoading(false));
  }, [enqueueSnackbar]);

  useEffect(() => {
    if (!profileId) return;
    loadMessages(profileId).catch(() => setRows([]));
  }, [profileId, loadMessages]);

  useEffect(() => {
    const leadId = params.get("lead");
    if (!leadId || params.get("to")) return;
    api
      .get<{ email?: string }>(`/crm/leads/${leadId}/`)
      .then((res) => {
        if (res.data.email) setTo((current) => current || res.data.email || "");
      })
      .catch(() => undefined);
  }, [params]);

  useEffect(() => {
    const opportunityId = params.get("opportunity");
    if (!opportunityId || params.get("to")) return;
    api
      .get<{ customer?: number | null }>(`/crm/opportunities/${opportunityId}/`)
      .then(async (res) => {
        if (!res.data.customer) return;
        const customer = await api.get<{ email?: string }>(`/sales/customers/${res.data.customer}/`);
        if (customer.data.email) setTo((current) => current || customer.data.email || "");
      })
      .catch(() => undefined);
  }, [params]);

  const selected = profiles.find((row) => String(row.id) === profileId);

  const send = async () => {
    if (!profileId || !to.trim() || !subject.trim()) return;
    setSending(true);
    try {
      const { data } = await api.post<MailRow>("/settings/mail-messages/send/", {
        profile: Number(profileId),
        to: to.trim(),
        subject: subject.trim(),
        body,
        lead: lead ? Number(lead) : null,
        opportunity: opportunity ? Number(opportunity) : null,
      });
      if (data.status === "sent") {
        enqueueSnackbar("Email sent", { variant: "success" });
        setSubject("");
        setBody("");
      } else {
        enqueueSnackbar(data.error || "Email was not sent", { variant: "error" });
      }
      await loadMessages(profileId);
    } catch (error) {
      enqueueSnackbar(getApiErrorMessage(error, "Could not send the email"), errorSnackbarOpts);
    } finally {
      setSending(false);
    }
  };

  const checkInbox = async () => {
    if (!profileId) return;
    setChecking(true);
    try {
      const { data } = await api.post<{ imported: number; skipped: number }>(
        "/settings/mail-messages/fetch/",
        { profile: Number(profileId) }
      );
      enqueueSnackbar(
        data.imported ? `Copied ${data.imported} message${data.imported === 1 ? "" : "s"}` : "No new mail",
        { variant: "success" }
      );
      await loadMessages(profileId);
    } catch (error) {
      enqueueSnackbar(getApiErrorMessage(error, "Could not check the inbox"), errorSnackbarOpts);
    } finally {
      setChecking(false);
    }
  };

  return (
    <>
      <PageHeader
        title="Mailbox"
        subtitle="Send, receive, and keep the trail on the lead or opportunity. The tenant SMTP or Microsoft 365 delivers the mail."
      />
      <Stack spacing={2}>
        <Stack direction={{ xs: "column", sm: "row" }} spacing={1} alignItems={{ sm: "center" }}>
          <TextField
            select
            label="Mailbox"
            value={profileId}
            onChange={(event) => setProfileId(event.target.value)}
            sx={{ minWidth: 280 }}
            disabled={loading || profiles.length === 0}
          >
            {profiles.map((row) => (
              <MenuItem key={row.id} value={String(row.id)}>
                {row.name} · {row.email}
              </MenuItem>
            ))}
          </TextField>
          <Button
            variant="outlined"
            disabled={!selected || selected.inbound === "none" || checking}
            onClick={() => void checkInbox()}
          >
            Check inbox
          </Button>
        </Stack>
        {profiles.length === 0 && !loading ? (
          <Typography variant="body2" color="text.secondary">
            Add a mailbox under Settings → Email. It can be shared, assigned to a full user, or assigned to an employee.
          </Typography>
        ) : null}
        <Paper variant="outlined" sx={{ p: 2 }}>
          <Typography variant="subtitle1" sx={{ mb: 1.5 }}>
            New message
          </Typography>
          <Stack spacing={1.5}>
            <TextField
              label="To"
              value={to}
              onChange={(event) => setTo(event.target.value)}
              helperText="Separate several addresses with a comma"
            />
            <TextField label="Subject" value={subject} onChange={(event) => setSubject(event.target.value)} />
            <TextField
              label="Message"
              value={body}
              multiline
              minRows={4}
              onChange={(event) => setBody(event.target.value)}
            />
            <Button
              variant="contained"
              sx={{ alignSelf: "flex-start" }}
              disabled={sending || !profileId || !to.trim() || !subject.trim()}
              onClick={() => void send()}
            >
              Send
            </Button>
          </Stack>
        </Paper>
        <Stack spacing={1}>
          {rows.map((row) => (
            <Paper key={row.id} variant="outlined" sx={{ p: 1.5 }}>
              <Stack direction="row" spacing={1} alignItems="center" useFlexGap flexWrap="wrap">
                <Chip
                  size="small"
                  label={directionLabel(row)}
                  color={row.status === "failed" ? "error" : row.direction === "in" ? "default" : "success"}
                  variant="outlined"
                />
                <Typography variant="body2" fontWeight={600}>
                  {row.subject || "(no subject)"}
                </Typography>
              </Stack>
              <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 0.5 }}>
                {row.direction === "in" ? `From ${row.from_email}` : `To ${row.to_emails}`}
              </Typography>
              {row.body ? (
                <Typography variant="body2" sx={{ mt: 1, whiteSpace: "pre-wrap" }}>
                  {row.body}
                </Typography>
              ) : null}
              {row.error ? (
                <Typography variant="body2" color="error" sx={{ mt: 1 }}>
                  {row.error}
                </Typography>
              ) : null}
            </Paper>
          ))}
          {!loading && profileId && rows.length === 0 ? (
            <Typography variant="body2" color="text.secondary">
              No mail tracked for this mailbox yet.
            </Typography>
          ) : null}
        </Stack>
      </Stack>
    </>
  );
}

export default function Page() {
  return (
    <Suspense fallback={null}>
      <MailboxScreen />
    </Suspense>
  );
}
