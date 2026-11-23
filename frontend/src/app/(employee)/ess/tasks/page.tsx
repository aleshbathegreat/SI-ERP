"use client";

import { useEffect, useRef, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Checkbox,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  MenuItem,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import DateTextField from "@/components/DateTextField";
import EssSection from "@/components/ess/EssSection";
import {
  EssTask,
  createEssTask,
  fetchEssTasks,
  patchEssTask,
  remindEssTask,
} from "@/lib/essApi";
import api from "@/lib/api";
import { errorSnackbarOpts, getApiErrorMessage } from "@/lib/apiError";
import { useSnackbar } from "notistack";

const COLUMNS = [
  { id: "open", label: "To do" },
  { id: "in_progress", label: "In progress" },
  { id: "in_review", label: "In review" },
  { id: "done", label: "Done" },
];

const PRIORITY: Record<string, "default" | "info" | "warning" | "error"> = {
  low: "default",
  medium: "info",
  high: "warning",
  urgent: "error",
};

export default function EssTasksPage() {
  const { enqueueSnackbar } = useSnackbar();
  const [rows, setRows] = useState<EssTask[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [priority, setPriority] = useState("medium");
  const [due, setDue] = useState("");
  const [assignee, setAssignee] = useState("");
  const [people, setPeople] = useState<{ id: number; name: string }[]>([]);
  const [busy, setBusy] = useState(false);
  const [drag, setDrag] = useState<{
    id: number;
    x: number;
    y: number;
    ox: number;
    oy: number;
    width: number;
  } | null>(null);
  const [over, setOver] = useState<string | null>(null);
  const dragRef = useRef<typeof drag>(null);

  const load = async () => {
    setLoading(true);
    setErr("");
    try {
      setRows(await fetchEssTasks());
    } catch (e: unknown) {
      setErr(getApiErrorMessage(e, "Could not load tasks"));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    api
      .get<{ id: number; name: string }[]>("/chat/people/")
      .then((res) => setPeople(res.data || []))
      .catch(() => setPeople([]));
  }, []);

  const move = async (task: EssTask, status: string) => {
    if (task.status === status) return;
    const previous = rows;
    setRows((prev) => prev.map((row) => (row.id === task.id ? { ...row, status } : row)));
    try {
      const next = await patchEssTask({ id: task.id, status });
      setRows((prev) => prev.map((row) => (row.id === task.id ? next : row)));
    } catch (e: unknown) {
      setRows(previous);
      enqueueSnackbar(getApiErrorMessage(e, "Could not move the task"), errorSnackbarOpts);
    }
  };

  const columnAt = (x: number, y: number) => {
    const hit = document.elementsFromPoint(x, y).find((node) => node instanceof HTMLElement && node.closest("[data-column]"));
    return hit instanceof HTMLElement ? hit.closest("[data-column]")?.getAttribute("data-column") : null;
  };

  const pointerDown = (event: React.PointerEvent<HTMLElement>, task: EssTask) => {
    if (event.button !== 0) return;
    const target = event.target as HTMLElement;
    if (target.closest("button, input, a, textarea, label")) return;
    const rect = event.currentTarget.getBoundingClientRect();
    event.currentTarget.setPointerCapture(event.pointerId);
    const next = {
      id: task.id,
      x: event.clientX,
      y: event.clientY,
      ox: event.clientX - rect.left,
      oy: event.clientY - rect.top,
      width: rect.width,
    };
    dragRef.current = next;
    setDrag(next);
  };

  const pointerMove = (event: React.PointerEvent<HTMLElement>) => {
    const current = dragRef.current;
    if (!current) return;
    const next = { ...current, x: event.clientX, y: event.clientY };
    dragRef.current = next;
    setDrag(next);
    setOver(columnAt(event.clientX, event.clientY));
  };

  const pointerUp = (event: React.PointerEvent<HTMLElement>) => {
    const current = dragRef.current;
    if (!current) return;
    const task = rows.find((row) => row.id === current.id);
    const status = columnAt(event.clientX, event.clientY);
    dragRef.current = null;
    setDrag(null);
    setOver(null);
    if (task && status && task.status !== status) void move(task, status);
  };

  const toggleItem = async (task: EssTask, index: number) => {
    const checklist = task.checklist.map((item, i) =>
      i === index ? { ...item, done: !item.done } : item,
    );
    try {
      const next = await patchEssTask({ id: task.id, checklist });
      setRows((prev) => prev.map((row) => (row.id === task.id ? next : row)));
    } catch (e: unknown) {
      enqueueSnackbar(getApiErrorMessage(e, "Could not update the checklist"), errorSnackbarOpts);
    }
  };

  const create = async () => {
    setBusy(true);
    try {
      await createEssTask({
        title,
        body,
        priority,
        due_date: due || undefined,
        assignee: assignee ? Number(assignee) : undefined,
      });
      setOpen(false);
      setTitle("");
      setBody("");
      setPriority("medium");
      setDue("");
      setAssignee("");
      await load();
    } catch (e: unknown) {
      enqueueSnackbar(getApiErrorMessage(e, "Could not create the task"), errorSnackbarOpts);
    } finally {
      setBusy(false);
    }
  };

  const remind = async (task: EssTask) => {
    try {
      await remindEssTask(task.id);
      enqueueSnackbar("Reminder sent", { variant: "success" });
    } catch (e: unknown) {
      enqueueSnackbar(getApiErrorMessage(e, "Could not send the reminder"), errorSnackbarOpts);
    }
  };

  if (loading) {
    return (
      <Box sx={{ display: "grid", placeItems: "center", minHeight: 240 }}>
        <CircularProgress size={32} />
      </Box>
    );
  }

  return (
    <EssSection
      title="Tasks"
      subtitle="Drag a card across To do, In progress, In review, and Done."
      action={
        <Button variant="contained" onClick={() => setOpen(true)}>
          New task
        </Button>
      }
    >
      {err ? <Alert severity="error" sx={{ mb: 2 }}>{err}</Alert> : null}
      <Box
        sx={{
          display: "flex",
          gap: 1.5,
          alignItems: "stretch",
          overflowX: "auto",
          pb: 1,
          mx: -0.5,
          px: 0.5,
        }}
      >
        {COLUMNS.map((column) => {
          const cards = rows.filter((row) => row.status === column.id);
          const active = over === column.id;
          return (
            <Box
              key={column.id}
              data-column={column.id}
              sx={{
                flex: "0 0 280px",
                minHeight: 420,
                p: 1.25,
                borderRadius: 2,
                bgcolor: active ? "action.selected" : "action.hover",
                outline: active ? "2px solid" : "1px dashed transparent",
                outlineColor: active ? "primary.main" : "transparent",
              }}
            >
              <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 1.25, px: 0.5 }}>
                <Typography fontWeight={700}>{column.label}</Typography>
                <Chip size="small" label={cards.length} />
              </Stack>
              <Stack spacing={1} data-column={column.id} sx={{ minHeight: 280 }}>
                {cards.length === 0 ? (
                  <Typography variant="body2" color="text.secondary" sx={{ px: 0.5 }} data-column={column.id}>
                    Drop a card here
                  </Typography>
                ) : null}
                {cards.map((task) => {
                  const doneCount = task.checklist.filter((item) => item.done).length;
                  const lifted = drag?.id === task.id;
                  return (
                    <Box
                      key={task.id}
                      onPointerDown={(event) => pointerDown(event, task)}
                      onPointerMove={pointerMove}
                      onPointerUp={pointerUp}
                      onPointerCancel={() => {
                        dragRef.current = null;
                        setDrag(null);
                        setOver(null);
                      }}
                      sx={{
                        p: 1.25,
                        borderRadius: 1.5,
                        bgcolor: "background.paper",
                        boxShadow: lifted ? 6 : 1,
                        cursor: lifted ? "grabbing" : "grab",
                        opacity: lifted ? 0.35 : 1,
                        touchAction: "none",
                        userSelect: "none",
                      }}
                    >
                      <Stack direction="row" justifyContent="space-between" spacing={1} alignItems="flex-start">
                        <Typography variant="body2" fontWeight={700}>{task.title}</Typography>
                        <Chip size="small" label={task.priority} color={PRIORITY[task.priority] || "default"} />
                      </Stack>
                      {task.body ? (
                        <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 0.5 }}>
                          {task.body}
                        </Typography>
                      ) : null}
                      <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 0.75 }}>
                        {[task.assignee_name, task.due_date].filter(Boolean).join(" · ") || "Unassigned"}
                      </Typography>
                      {task.checklist.length ? (
                        <Typography variant="caption" color="text.secondary">
                          {doneCount}/{task.checklist.length} checklist
                        </Typography>
                      ) : null}
                      {task.checklist.map((item, index) => (
                        <Stack key={`${task.id}-${index}`} direction="row" alignItems="center">
                          <Checkbox
                            size="small"
                            checked={item.done}
                            onChange={() => toggleItem(task, index)}
                          />
                          <Typography variant="body2" sx={{ textDecoration: item.done ? "line-through" : "none" }}>
                            {item.text}
                          </Typography>
                        </Stack>
                      ))}
                      {task.can_remind ? (
                        <Button size="small" sx={{ mt: 0.5 }} onClick={() => remind(task)}>
                          Send reminder
                        </Button>
                      ) : null}
                    </Box>
                  );
                })}
              </Stack>
            </Box>
          );
        })}
      </Box>
      {drag ? (
        <Box
          sx={{
            position: "fixed",
            left: drag.x - drag.ox,
            top: drag.y - drag.oy,
            width: drag.width,
            zIndex: 1400,
            pointerEvents: "none",
            p: 1.25,
            borderRadius: 1.5,
            bgcolor: "background.paper",
            boxShadow: 8,
            transform: "rotate(2deg)",
          }}
        >
          <Typography variant="body2" fontWeight={700}>
            {rows.find((row) => row.id === drag.id)?.title}
          </Typography>
        </Box>
      ) : null}
      <Dialog open={open} onClose={() => setOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>New task</DialogTitle>
        <DialogContent>
          <Stack spacing={1.5} sx={{ mt: 1 }}>
            <TextField label="Title" value={title} onChange={(e) => setTitle(e.target.value)} />
            <TextField label="Details" value={body} onChange={(e) => setBody(e.target.value)} multiline minRows={2} />
            <TextField select label="Priority" value={priority} onChange={(e) => setPriority(e.target.value)}>
              {["low", "medium", "high", "urgent"].map((item) => (
                <MenuItem key={item} value={item}>{item}</MenuItem>
              ))}
            </TextField>
            <DateTextField label="Due date" value={due} showFormatHint onChange={(e) => setDue(e.target.value)} />
            <TextField select label="Assign to" value={assignee} onChange={(e) => setAssignee(e.target.value)}>
              <MenuItem value="">Myself</MenuItem>
              {people.map((person) => (
                <MenuItem key={person.id} value={String(person.id)}>{person.name}</MenuItem>
              ))}
            </TextField>
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpen(false)}>Cancel</Button>
          <Button variant="contained" disabled={busy || !title.trim()} onClick={create}>Create</Button>
        </DialogActions>
      </Dialog>
    </EssSection>
  );
}
