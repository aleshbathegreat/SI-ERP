"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
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
import api from "@/lib/api";
import { getApiErrorMessage, errorSnackbarOpts } from "@/lib/apiError";
import { usePermissions } from "@/hooks/usePermissions";

type ActivityRow = {
  id: number;
  type: string;
  subject: string;
  due_date: string | null;
  done: boolean;
  is_overdue: boolean;
  owner_name: string;
};

type Props = {
  leadId?: number;
  opportunityId?: number;
  toEmail?: string;
};

const TYPES = [
  { value: "call", label: "Call" },
  { value: "email", label: "Email" },
  { value: "meeting", label: "Meeting" },
  { value: "task", label: "Task" },
];

function dayLabel(value?: string | null) {
  if (!value) return "No date";
  const [year, month, day] = value.slice(0, 10).split("-").map(Number);
  if (!year || !month || !day) return value;
  return new Date(year, month - 1, day).toLocaleDateString("en-GB", {
    day: "2-digit",
    month: "short",
  });
}

export default function RecordActivities({ leadId, opportunityId, toEmail }: Props) {
  const { enqueueSnackbar } = useSnackbar();
  const { canAdd, canChange, canView } = usePermissions();
  const [rows, setRows] = useState<ActivityRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [type, setType] = useState("call");
  const [subject, setSubject] = useState("");
  const [due, setDue] = useState("");
  const [saving, setSaving] = useState(false);

  const load = useCallback(() => {
    const params = new URLSearchParams();
    if (leadId) params.set("lead", String(leadId));
    if (opportunityId) params.set("opportunity", String(opportunityId));
    setLoading(true);
    api
      .get<{ results?: ActivityRow[] } | ActivityRow[]>(`/crm/activities/?${params.toString()}`)
      .then((res) => {
        const data = res.data;
        setRows(Array.isArray(data) ? data : data.results || []);
      })
      .catch(() => setRows([]))
      .finally(() => setLoading(false));
  }, [leadId, opportunityId]);

  useEffect(() => {
    load();
  }, [load]);

  const schedule = async () => {
    if (!subject.trim()) return;
    setSaving(true);
    try {
      await api.post("/crm/activities/", {
        type,
        subject: subject.trim(),
        due_date: due || null,
        priority: "normal",
        lead: leadId || null,
        opportunity: opportunityId || null,
      });
      setSubject("");
      setDue("");
      enqueueSnackbar("Activity scheduled", { variant: "success" });
      load();
    } catch (error) {
      enqueueSnackbar(getApiErrorMessage(error, "Could not schedule the activity"), errorSnackbarOpts);
    } finally {
      setSaving(false);
    }
  };

  const complete = async (id: number) => {
    try {
      await api.post(`/crm/activities/${id}/complete/`, {});
      enqueueSnackbar("Activity marked done", { variant: "success" });
      load();
    } catch (error) {
      enqueueSnackbar(getApiErrorMessage(error, "Could not mark the activity done"), errorSnackbarOpts);
    }
  };

  const query = new URLSearchParams();
  if (leadId) query.set("lead", String(leadId));
  if (opportunityId) query.set("opportunity", String(opportunityId));
  const mailQuery = new URLSearchParams(query);
  if (toEmail) mailQuery.set("to", toEmail);

  return (
    <Paper variant="outlined" sx={{ p: 2, mt: 2 }}>
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1.5 }}>
        <Typography variant="subtitle1">Activities</Typography>
        <Stack direction="row" spacing={1}>
          {canView("settings.email") ? (
            <Button component={Link} href={`/settings/mailbox?${mailQuery.toString()}`} size="small">
              Email
            </Button>
          ) : null}
          <Button component={Link} href={`/crm/activities/new?${query.toString()}`} size="small">
            Full form
          </Button>
        </Stack>
      </Stack>
      {canAdd("crm.activities") ? (
        <Stack direction={{ xs: "column", sm: "row" }} spacing={1} sx={{ mb: 2 }}>
          <TextField
            select
            size="small"
            label="Type"
            value={type}
            onChange={(event) => setType(event.target.value)}
            sx={{ minWidth: 120 }}
          >
            {TYPES.map((item) => (
              <MenuItem key={item.value} value={item.value}>
                {item.label}
              </MenuItem>
            ))}
          </TextField>
          <TextField
            size="small"
            label="Subject"
            value={subject}
            onChange={(event) => setSubject(event.target.value)}
            fullWidth
          />
          <TextField
            size="small"
            label="Due"
            type="date"
            value={due}
            onChange={(event) => setDue(event.target.value)}
            slotProps={{ inputLabel: { shrink: true } }}
            sx={{ minWidth: 150 }}
          />
          <Button variant="contained" disabled={saving || !subject.trim()} onClick={() => void schedule()}>
            Schedule
          </Button>
        </Stack>
      ) : null}
      {loading ? (
        <Typography variant="body2" color="text.secondary">
          Loading…
        </Typography>
      ) : rows.length === 0 ? (
        <Typography variant="body2" color="text.secondary">
          No calls, meetings, or tasks on this record yet.
        </Typography>
      ) : (
        <Stack spacing={1}>
          {rows.map((row) => (
            <Stack
              key={row.id}
              direction="row"
              spacing={1}
              alignItems="center"
              justifyContent="space-between"
            >
              <Stack direction="row" spacing={1} alignItems="center" useFlexGap flexWrap="wrap">
                <Chip size="small" label={row.type} variant="outlined" />
                <Typography
                  variant="body2"
                  sx={{ textDecoration: row.done ? "line-through" : "none" }}
                >
                  {row.subject}
                </Typography>
                <Typography variant="caption" color={row.is_overdue ? "error" : "text.secondary"}>
                  {row.is_overdue ? "Overdue · " : ""}
                  {dayLabel(row.due_date)}
                  {row.owner_name ? ` · ${row.owner_name}` : ""}
                </Typography>
              </Stack>
              {!row.done && canChange("crm.activities") ? (
                <Button size="small" onClick={() => void complete(row.id)}>
                  Done
                </Button>
              ) : null}
            </Stack>
          ))}
        </Stack>
      )}
    </Paper>
  );
}
