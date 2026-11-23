"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Box,
  Button,
  Chip,
  Paper,
  Stack,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from "@mui/material";
import { useSnackbar } from "notistack";
import api from "@/lib/api";
import { errorSnackbarOpts, getApiErrorMessage } from "@/lib/apiError";
import ModuleGate from "@/components/ModuleGate";

type CalEvent = {
  id: number;
  subject: string;
  type: string;
  done: boolean;
  location: string;
  starts_at: string | null;
  ends_at: string | null;
  due_date: string | null;
  all_day: boolean;
  is_overdue: boolean;
  lead_name: string;
  opportunity_name: string;
  owner_name: string;
};

const WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

function pad(value: number) {
  return String(value).padStart(2, "0");
}

function ymd(date: Date) {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

function monthStart(year: number, month: number) {
  return new Date(year, month, 1);
}

function addMonth(year: number, month: number, delta: number) {
  const next = new Date(year, month + delta, 1);
  return { year: next.getFullYear(), month: next.getMonth() };
}

function eventDay(event: CalEvent) {
  if (event.starts_at) {
    const parsed = new Date(event.starts_at);
    if (!Number.isNaN(parsed.getTime())) return ymd(parsed);
  }
  return event.due_date || "";
}

function clock(value?: string | null) {
  if (!value) return "";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "";
  return parsed.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });
}

function icsStamp(value: string) {
  const parsed = new Date(value);
  const utc = new Date(parsed.getTime());
  return (
    `${utc.getUTCFullYear()}${pad(utc.getUTCMonth() + 1)}${pad(utc.getUTCDate())}` +
    `T${pad(utc.getUTCHours())}${pad(utc.getUTCMinutes())}00Z`
  );
}

function escapeIcs(value: string) {
  return value.replace(/\\/g, "\\\\").replace(/\n/g, "\\n").replace(/,/g, "\\,").replace(/;/g, "\\;");
}

function buildIcs(events: CalEvent[]) {
  const lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//SIERP//CRM//EN", "CALSCALE:GREGORIAN"];
  for (const event of events) {
    lines.push("BEGIN:VEVENT");
    lines.push(`UID:crm-activity-${event.id}@si-erp.mushaz.com`);
    lines.push(`SUMMARY:${escapeIcs(event.subject)}`);
    if (event.location) lines.push(`LOCATION:${escapeIcs(event.location)}`);
    const detail = [event.lead_name, event.opportunity_name].filter(Boolean).join(" · ");
    if (detail) lines.push(`DESCRIPTION:${escapeIcs(detail)}`);
    if (event.starts_at) {
      lines.push(`DTSTART:${icsStamp(event.starts_at)}`);
      const end = event.ends_at
        ? event.ends_at
        : new Date(new Date(event.starts_at).getTime() + 30 * 60 * 1000).toISOString();
      lines.push(`DTEND:${icsStamp(end)}`);
    } else if (event.due_date) {
      const compact = event.due_date.slice(0, 10).replace(/-/g, "");
      const day = new Date(`${event.due_date.slice(0, 10)}T00:00:00`);
      day.setDate(day.getDate() + 1);
      const end = `${day.getFullYear()}${pad(day.getMonth() + 1)}${pad(day.getDate())}`;
      lines.push(`DTSTART;VALUE=DATE:${compact}`);
      lines.push(`DTEND;VALUE=DATE:${end}`);
    }
    lines.push("END:VEVENT");
  }
  lines.push("END:VCALENDAR");
  return lines.join("\r\n");
}

export default function Page() {
  const router = useRouter();
  const { enqueueSnackbar } = useSnackbar();
  const today = useMemo(() => new Date(), []);
  const [cursor, setCursor] = useState({ year: today.getFullYear(), month: today.getMonth() });
  const [events, setEvents] = useState<CalEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [mine, setMine] = useState(false);
  const [kind, setKind] = useState("all");
  const [selected, setSelected] = useState(ymd(today));
  const [targets, setTargets] = useState<{ key: string; name: string }[]>([]);

  useEffect(() => {
    if (window.sessionStorage.getItem("crm-cal-mine") === "1") setMine(true);
    api
      .get<{ key: string; name: string }[]>("/crm/activities/calendar-targets/")
      .then((res) => setTargets(res.data || []))
      .catch(() => setTargets([]));
  }, []);

  const load = useCallback(() => {
    const start = monthStart(cursor.year, cursor.month);
    const end = monthStart(cursor.year, cursor.month + 1);
    const params = new URLSearchParams({ start: ymd(start), end: ymd(end) });
    if (mine) params.set("mine", "1");
    if (kind !== "all") params.set("type", kind);
    setLoading(true);
    api
      .get<CalEvent[]>(`/crm/activities/calendar/?${params.toString()}`)
      .then((res) => setEvents(res.data))
      .catch((error) => {
        setEvents([]);
        enqueueSnackbar(getApiErrorMessage(error, "Could not load the calendar"), errorSnackbarOpts);
      })
      .finally(() => setLoading(false));
  }, [cursor.month, cursor.year, enqueueSnackbar, kind, mine]);

  useEffect(() => {
    load();
  }, [load]);

  const byDay = useMemo(() => {
    const map = new Map<string, CalEvent[]>();
    for (const event of events) {
      const key = eventDay(event);
      if (!key) continue;
      const list = map.get(key) || [];
      list.push(event);
      map.set(key, list);
    }
    return map;
  }, [events]);

  const cells = useMemo(() => {
    const first = monthStart(cursor.year, cursor.month);
    const offset = (first.getDay() + 6) % 7;
    const count = new Date(cursor.year, cursor.month + 1, 0).getDate();
    const days: Array<Date | null> = [];
    for (let index = 0; index < offset; index += 1) days.push(null);
    for (let day = 1; day <= count; day += 1) days.push(new Date(cursor.year, cursor.month, day));
    while (days.length % 7) days.push(null);
    return days;
  }, [cursor.month, cursor.year]);

  const selectedEvents = byDay.get(selected) || [];
  const title = monthStart(cursor.year, cursor.month).toLocaleDateString("en-GB", {
    month: "long",
    year: "numeric",
  });

  const download = () => {
    const blob = new Blob([buildIcs(events)], { type: "text/calendar;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `sierp-crm-${cursor.year}-${pad(cursor.month + 1)}.ics`;
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <ModuleGate module="crm.activities">
      <Stack spacing={2}>
        <Stack direction={{ xs: "column", md: "row" }} spacing={1} justifyContent="space-between">
          <Stack direction="row" spacing={1} alignItems="center">
            <Button onClick={() => setCursor((value) => addMonth(value.year, value.month, -1))}>
              Previous
            </Button>
            <Typography variant="h6" sx={{ minWidth: 160, textAlign: "center" }}>
              {title}
            </Typography>
            <Button onClick={() => setCursor((value) => addMonth(value.year, value.month, 1))}>
              Next
            </Button>
            <Button
              onClick={() => {
                setCursor({ year: today.getFullYear(), month: today.getMonth() });
                setSelected(ymd(today));
              }}
            >
              Today
            </Button>
          </Stack>
          <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap">
            <ToggleButtonGroup
              size="small"
              exclusive
              value={mine ? "mine" : "all"}
              onChange={(_, next: string | null) => {
                if (!next) return;
                const value = next === "mine";
                setMine(value);
                window.sessionStorage.setItem("crm-cal-mine", value ? "1" : "0");
              }}
            >
              <ToggleButton value="all">Everyone</ToggleButton>
              <ToggleButton value="mine">Mine</ToggleButton>
            </ToggleButtonGroup>
            <Button variant="outlined" onClick={download} disabled={events.length === 0}>
              Download .ics
            </Button>
            <Button
              variant="contained"
              component={Link}
              href={`/crm/activities/new?due=${selected}&start=${selected}T09:00&end=${selected}T09:30`}
            >
              Schedule
            </Button>
          </Stack>
        </Stack>

        {targets.length > 0 ? (
          <Typography variant="body2" color="text.secondary">
            Also copying meetings to {targets.map((item) => item.name).join(", ")}. SI-ERP remains the record.
          </Typography>
        ) : null}

        <ToggleButtonGroup
          size="small"
          exclusive
          value={kind}
          onChange={(_, next: string | null) => next && setKind(next)}
        >
          {[
            ["all", "All"],
            ["call", "Calls"],
            ["meeting", "Meetings"],
            ["email", "Email"],
            ["task", "Tasks"],
          ].map(([value, label]) => (
            <ToggleButton key={value} value={value}>
              {label}
            </ToggleButton>
          ))}
        </ToggleButtonGroup>

        <Paper variant="outlined" sx={{ overflowX: "auto" }}>
          <Box sx={{ minWidth: 760 }}>
            <Box
              sx={{
                display: "grid",
                gridTemplateColumns: "repeat(7, 1fr)",
                borderBottom: 1,
                borderColor: "divider",
              }}
            >
              {WEEKDAYS.map((day) => (
                <Typography
                  key={day}
                  variant="caption"
                  color="text.secondary"
                  sx={{ px: 1, py: 0.75 }}
                >
                  {day}
                </Typography>
              ))}
            </Box>
            <Box sx={{ display: "grid", gridTemplateColumns: "repeat(7, 1fr)" }}>
              {cells.map((date, index) => {
                const key = date ? ymd(date) : `empty-${index}`;
                const dayEvents = date ? byDay.get(key) || [] : [];
                const isToday = date ? key === ymd(today) : false;
                const isSelected = date ? key === selected : false;
                return (
                  <Box
                    key={key}
                    onClick={() => date && setSelected(key)}
                    sx={{
                      minHeight: 108,
                      p: 0.75,
                      borderTop: 1,
                      borderLeft: index % 7 === 0 ? 0 : 1,
                      borderColor: "divider",
                      bgcolor: isSelected ? "action.selected" : "transparent",
                      cursor: date ? "pointer" : "default",
                    }}
                  >
                    {date ? (
                      <>
                        <Typography
                          variant="caption"
                          sx={{ fontWeight: isToday ? 700 : 500 }}
                          color={isToday ? "primary" : "text.primary"}
                        >
                          {date.getDate()}
                        </Typography>
                        <Stack spacing={0.25} sx={{ mt: 0.5 }}>
                          {dayEvents.slice(0, 3).map((event) => (
                            <Chip
                              key={event.id}
                              size="small"
                              label={`${event.all_day ? "" : `${clock(event.starts_at)} `}${event.subject}`}
                              color={event.is_overdue ? "error" : event.type === "meeting" ? "primary" : "default"}
                              variant={event.done ? "outlined" : "filled"}
                              onClick={(click) => {
                                click.stopPropagation();
                                router.push(`/crm/activities/${event.id}`);
                              }}
                              sx={{
                                justifyContent: "flex-start",
                                height: 22,
                                "& .MuiChip-label": { px: 0.75, fontSize: 11 },
                              }}
                            />
                          ))}
                          {dayEvents.length > 3 ? (
                            <Typography variant="caption" color="text.secondary">
                              +{dayEvents.length - 3} more
                            </Typography>
                          ) : null}
                        </Stack>
                      </>
                    ) : null}
                  </Box>
                );
              })}
            </Box>
          </Box>
        </Paper>

        <Paper variant="outlined" sx={{ p: 2 }}>
          <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
            <Typography variant="subtitle1">
              {loading ? "Loading…" : selected}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {events.length} this month
            </Typography>
          </Stack>
          {selectedEvents.length === 0 ? (
            <Typography variant="body2" color="text.secondary">
              Nothing scheduled. Use Schedule to put a call or meeting on this day. Link it to a lead or an opportunity before saving.
            </Typography>
          ) : (
            <Stack spacing={1}>
              {selectedEvents.map((event) => (
                <Stack
                  key={event.id}
                  direction={{ xs: "column", sm: "row" }}
                  spacing={1}
                  justifyContent="space-between"
                  alignItems={{ sm: "center" }}
                >
                  <Stack direction="row" spacing={1} alignItems="center" useFlexGap flexWrap="wrap">
                    <Chip size="small" label={event.type} variant="outlined" />
                    <Typography
                      variant="body2"
                      sx={{ textDecoration: event.done ? "line-through" : "none" }}
                    >
                      {event.all_day ? "All day" : `${clock(event.starts_at)}${event.ends_at ? `–${clock(event.ends_at)}` : ""}`}
                      {" · "}
                      {event.subject}
                    </Typography>
                    <Typography variant="caption" color={event.is_overdue ? "error" : "text.secondary"}>
                      {[event.location, event.lead_name || event.opportunity_name, event.owner_name]
                        .filter(Boolean)
                        .join(" · ")}
                    </Typography>
                  </Stack>
                  <Button size="small" onClick={() => router.push(`/crm/activities/${event.id}`)}>
                    Open
                  </Button>
                </Stack>
              ))}
            </Stack>
          )}
        </Paper>
      </Stack>
    </ModuleGate>
  );
}
