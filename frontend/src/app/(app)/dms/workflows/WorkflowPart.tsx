"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Button,
  Checkbox,
  FormControlLabel,
  MenuItem,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";
import { useSnackbar } from "notistack";
import PageHeader from "@/components/PageHeader";
import ConfirmDialog from "@/components/crud/ConfirmDialog";
import RowActionsMenu from "@/components/crud/RowActionsMenu";
import api from "@/lib/api";
import { errorSnackbarOpts, getApiErrorMessage } from "@/lib/apiError";
import { listResource } from "@/lib/crudApi";
import { formatDateTime } from "@/lib/format";
import { RECORD_HREF, workflowTargetLabel } from "./workflowTargets";

export const WORKFLOW_PARTS = [
  { key: "states", title: "States" },
  { key: "transitions", title: "Transitions" },
  { key: "events", title: "Events" },
  { key: "fields", title: "Fields" },
  { key: "triggers", title: "Triggers" },
  { key: "actions", title: "Actions" },
  { key: "escalations", title: "Escalations" },
  { key: "records", title: "Records" },
] as const;

const PART_API: Record<string, string> = {
  states: "/dms/workflow-states/",
  transitions: "/dms/workflow-transitions/",
  events: "/dms/workflow-transition-events/",
  fields: "/dms/workflow-transition-fields/",
  triggers: "/dms/workflow-triggers/",
  actions: "/dms/workflow-actions/",
  escalations: "/dms/workflow-states/",
  records: "/dms/workflow-cases/",
};

const EVENT_LABELS: Record<string, string> = {
  on_enter: "On enter",
  on_leave: "On leave",
  on_overdue: "On escalation",
};

const ACTION_LABELS: Record<string, string> = {
  set_status: "Set status",
  notify: "Notify",
  notify_role: "Notify a role",
  add_comment: "Add comment",
  create_task: "Create a task",
};

const RECORD_EVENTS = [
  { value: "record.created", label: "Record created" },
  { value: "record.updated", label: "Record updated" },
  { value: "record.submitted", label: "Record submitted" },
  { value: "record.approved", label: "Record approved" },
  { value: "record.rejected", label: "Record rejected" },
  { value: "record.posted", label: "Record posted" },
];

type Row = { id: number } & Record<string, unknown>;

export function isWorkflowPart(part: string) {
  return WORKFLOW_PARTS.some((row) => row.key === part);
}

function textOrEmpty(value: unknown) {
  if (value === null || value === undefined) return "";
  return String(value);
}

function text(value: unknown) {
  if (value === null || value === undefined || value === "") return "—";
  return String(value);
}

function yes(value: unknown) {
  return value ? "Yes" : "No";
}

export function WorkflowPart({
  workflowId,
  part,
  mode,
  childId,
}: {
  workflowId: string;
  part: string;
  mode: "list" | "new" | "view" | "edit";
  childId?: string;
}) {
  const router = useRouter();
  const { enqueueSnackbar } = useSnackbar();
  const meta = WORKFLOW_PARTS.find((row) => row.key === part);
  const [name, setName] = useState("");
  const [rows, setRows] = useState<Row[]>([]);
  const [states, setStates] = useState<Row[]>([]);
  const [transitions, setTransitions] = useState<Row[]>([]);
  const [triggers, setTriggers] = useState<Row[]>([]);
  const [roles, setRoles] = useState<Row[]>([]);
  const [loading, setLoading] = useState(mode === "list" || mode === "edit");
  const [current, setCurrent] = useState<Row | null>(null);
  const [pendingDelete, setPendingDelete] = useState<Row | null>(null);
  const [deleting, setDeleting] = useState(false);

  const back = `/dms/workflows/${workflowId}/${part}`;

  const load = async () => {
    setLoading(true);
    try {
      const [workflow, stateRows, transitionRows, triggerRows] = await Promise.all([
        api.get(`/dms/workflows/${workflowId}/`),
        listResource<Row>("/dms/workflow-states/", { workflow: workflowId }),
        listResource<Row>("/dms/workflow-transitions/", { workflow: workflowId }),
        listResource<Row>("/dms/workflow-triggers/", { workflow: workflowId }),
      ]);
      setName(String(workflow.data?.name || "Workflow"));
      setStates(stateRows);
      setTransitions(transitionRows);
      setTriggers(triggerRows);
      try {
        setRoles(await listResource<Row>("/settings/roles/"));
      } catch {
        setRoles([]);
      }
      if (mode === "list") {
        const data = await listResource<Row>(PART_API[part], { workflow: workflowId });
        setRows(data);
      }
      if ((mode === "view" || mode === "edit") && childId) {
        const detail = await api.get(`${PART_API[part]}${childId}/`);
        setCurrent(detail.data);
      }
    } catch (e) {
      enqueueSnackbar(getApiErrorMessage(e, "Could not load this workflow"), errorSnackbarOpts);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [workflowId, part, mode]);

  const save = async (path: string, body: unknown, ok: string, method: "post" | "patch" = "post") => {
    try {
      await api[method](path, body);
      enqueueSnackbar(ok, { variant: "success" });
      router.push(back);
    } catch (e) {
      enqueueSnackbar(getApiErrorMessage(e, "Save failed"), errorSnackbarOpts);
    }
  };

  const remove = async () => {
    if (!pendingDelete) return;
    setDeleting(true);
    try {
      await api.delete(`${PART_API[part]}${pendingDelete.id}/`);
      enqueueSnackbar("Removed", { variant: "success" });
      setPendingDelete(null);
      await load();
    } catch (e) {
      enqueueSnackbar(getApiErrorMessage(e, "Could not remove that row"), errorSnackbarOpts);
    } finally {
      setDeleting(false);
    }
  };

  if (!meta) return null;
  const editable = ["states", "transitions", "events", "fields", "triggers", "actions", "escalations"].includes(part);
  const canAdd = mode === "list" && ["states", "transitions", "events", "fields", "triggers", "actions"].includes(part);
  const canDelete = ["states", "transitions", "events", "fields", "triggers", "actions"].includes(part);
  const showForm = (key: string) =>
    part === key && (mode === "new" || ((mode === "view" || mode === "edit") && !!current));
  const singular = meta.title.endsWith("s") ? meta.title.slice(0, -1) : meta.title;
  const title =
    mode === "new" ? `Add ${singular.toLowerCase()}` : mode === "edit" ? `Edit ${singular.toLowerCase()}` : mode === "view" ? singular : meta.title;

  return (
    <>
      <PageHeader
        title={title}
        subtitle={name || "Workflow"}
        actions={
          <Stack direction="row" spacing={1}>
            <Button component={Link} href="/dms/workflows" variant="text">
              All workflows
            </Button>
            <Button component={Link} href={`/dms/workflows/${workflowId}`} variant="outlined">
              Preview
            </Button>
            {mode === "view" && editable && childId ? (
              <Button component={Link} href={`${back}/${childId}/edit`} variant="contained">
                Edit
              </Button>
            ) : null}
            {canAdd ? (
              <Button component={Link} href={`${back}/new`} variant="contained">
                Add
              </Button>
            ) : null}
          </Stack>
        }
      />
      <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap" sx={{ mb: 2 }}>
        {WORKFLOW_PARTS.map((row) => (
          <Button
            key={row.key}
            component={Link}
            href={`/dms/workflows/${workflowId}/${row.key}`}
            size="small"
            variant={row.key === part ? "contained" : "text"}
          >
            {row.title}
          </Button>
        ))}
      </Stack>
      {(mode === "view" || mode === "edit") && loading ? (
        <Typography sx={{ mb: 2 }} color="text.secondary">
          Loading…
        </Typography>
      ) : null}
      {mode === "list" ? (
        <Paper variant="outlined">
          {loading ? (
            <Typography sx={{ p: 2 }} color="text.secondary">
              Loading…
            </Typography>
          ) : rows.length === 0 ? (
            <Typography sx={{ p: 2 }} color="text.secondary">
              {part === "records"
                ? "Records appear here when a matching journal, leave request, order, or other record is submitted, approved, rejected, or posted."
                : "Nothing here yet."}
            </Typography>
          ) : (
            <Table size="small">
              <TableHead>
                <TableRow>
                  {headers(part).map((header) => (
                    <TableCell key={header}>{header}</TableCell>
                  ))}
                  <TableCell />
                </TableRow>
              </TableHead>
              <TableBody>
                {rows.map((row) => (
                  <TableRow key={row.id} hover>
                    {cells(part, row, states, transitions, triggers).map((value, index) => (
                      <TableCell key={index}>{value}</TableCell>
                    ))}
                    <TableCell align="right">
                      <RowActionsMenu
                        onView={() => router.push(`${back}/${row.id}`)}
                        onEdit={editable ? () => router.push(`${back}/${row.id}/edit`) : undefined}
                        onDelete={canDelete ? () => setPendingDelete(row) : undefined}
                      />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </Paper>
      ) : null}
      {showForm("states") ? (
        <StateForm
          initial={current}
          readOnly={mode === "view"}
          onSubmit={(body) =>
            save(
              mode === "edit" ? `/dms/workflow-states/${childId}/` : "/dms/workflow-states/",
              mode === "edit" ? body : { ...body, workflow: workflowId },
              mode === "edit" ? "State saved" : "State added",
              mode === "edit" ? "patch" : "post"
            )
          }
        />
      ) : null}
      {showForm("transitions") ? (
        <TransitionForm
          initial={current}
          readOnly={mode === "view"}
          states={states}
          roles={roles}
          onSubmit={async (body) => {
            const events = (body.events as string[]) || [];
            const rest = { ...body };
            delete rest.events;
            try {
              const id =
                mode === "edit" && childId
                  ? childId
                  : String((await api.post("/dms/workflow-transitions/", { ...rest, workflow: workflowId })).data.id);
              if (mode === "edit") {
                await api.patch(`/dms/workflow-transitions/${id}/`, rest);
              }
              const existing =
                mode === "edit"
                  ? await listResource<Row>("/dms/workflow-transition-events/", {
                      workflow: workflowId,
                      transition: id,
                    })
                  : [];
              const have = new Set(existing.map((row) => String(row.event)));
              const want = new Set(events);
              await Promise.all([
                ...existing
                  .filter((row) => !want.has(String(row.event)))
                  .map((row) => api.delete(`/dms/workflow-transition-events/${row.id}/`)),
                ...events
                  .filter((event) => !have.has(event))
                  .map((event) =>
                    api.post("/dms/workflow-transition-events/", {
                      workflow: workflowId,
                      transition: id,
                      event,
                    })
                  ),
              ]);
              enqueueSnackbar(mode === "edit" ? "Transition saved" : "Transition added", { variant: "success" });
              router.push(back);
            } catch (e) {
              enqueueSnackbar(getApiErrorMessage(e, "Save failed"), errorSnackbarOpts);
            }
          }}
        />
      ) : null}
      {showForm("events") ? (
        <EventForm
          initial={current}
          readOnly={mode === "view"}
          transitions={transitions}
          onSubmit={(body) =>
            save(
              mode === "edit" ? `/dms/workflow-transition-events/${childId}/` : "/dms/workflow-transition-events/",
              mode === "edit" ? body : { ...body, workflow: workflowId },
              mode === "edit" ? "Event saved" : "Event added",
              mode === "edit" ? "patch" : "post"
            )
          }
        />
      ) : null}
      {showForm("fields") ? (
        <FieldForm
          initial={current}
          readOnly={mode === "view"}
          transitions={transitions}
          onSubmit={(body) =>
            save(
              mode === "edit" ? `/dms/workflow-transition-fields/${childId}/` : "/dms/workflow-transition-fields/",
              mode === "edit" ? body : { ...body, workflow: workflowId },
              mode === "edit" ? "Field saved" : "Field added",
              mode === "edit" ? "patch" : "post"
            )
          }
        />
      ) : null}
      {showForm("triggers") ? (
        <TriggerForm
          initial={current}
          readOnly={mode === "view"}
          states={states}
          onSubmit={(body) =>
            save(
              mode === "edit" ? `/dms/workflow-triggers/${childId}/` : "/dms/workflow-triggers/",
              mode === "edit" ? body : { ...body, workflow: workflowId },
              mode === "edit" ? "Trigger saved" : "Trigger added",
              mode === "edit" ? "patch" : "post"
            )
          }
        />
      ) : null}
      {showForm("actions") ? (
        <ActionForm
          initial={current}
          readOnly={mode === "view"}
          transitions={transitions}
          triggers={triggers}
          onSubmit={(body) =>
            save(
              mode === "edit" ? `/dms/workflow-actions/${childId}/` : "/dms/workflow-actions/",
              mode === "edit" ? body : { ...body, workflow: workflowId },
              mode === "edit" ? "Action saved" : "Action added",
              mode === "edit" ? "patch" : "post"
            )
          }
        />
      ) : null}
      {showForm("escalations") && childId ? (
        <EscalationForm
          states={states}
          childId={childId}
          readOnly={mode === "view"}
          onSubmit={(body) => save(`/dms/workflow-states/${childId}/`, body, "Escalation saved", "patch")}
        />
      ) : null}
      {mode === "view" && part === "records" && current ? <RecordView row={current} /> : null}
      <ConfirmDialog
        open={!!pendingDelete}
        title="Delete this row?"
        message="This deletes it from the workflow."
        confirmLabel="Delete"
        loading={deleting}
        onClose={() => setPendingDelete(null)}
        onConfirm={() => void remove()}
      />
    </>
  );
}

function headers(part: string) {
  if (part === "states") return ["Name", "Code", "Initial", "Terminal", "Hours", "Record status"];
  if (part === "transitions") return ["Action", "From", "To", "Roles", "Events", "Comment", "Signature", "SoD"];
  if (part === "events") return ["Transition", "Event"];
  if (part === "fields") return ["Label", "Name", "Type", "Required", "Transition"];
  if (part === "triggers") return ["When", "State"];
  if (part === "actions") return ["Type", "Transition", "Trigger", "Message"];
  if (part === "escalations") return ["State", "Hours", "Escalate to"];
  return ["Area", "Record", "State", "Entered"];
}

function cells(part: string, row: Row, states: Row[], transitions: Row[], triggers: Row[]) {
  if (part === "states") {
    return [
      text(row.name),
      text(row.code),
      yes(row.is_initial),
      yes(row.is_terminal),
      text(row.escalation_hours),
      text(row.document_status),
    ];
  }
  if (part === "transitions") {
    const roles = Array.isArray(row.role_names) ? row.role_names.join(", ") : "";
    const events = Array.isArray(row.event_codes)
      ? row.event_codes.map((code) => RECORD_EVENTS.find((item) => item.value === code)?.label || String(code)).join(", ")
      : "";
    return [
      text(row.label),
      text(row.from_name),
      text(row.to_name),
      roles || "Anyone",
      events || "—",
      yes(row.require_comment),
      yes(row.require_signature),
      yes(row.block_self_approval),
    ];
  }
  if (part === "events") {
    const label = RECORD_EVENTS.find((item) => item.value === row.event)?.label || text(row.event);
    return [text(row.transition_label), label];
  }
  if (part === "fields") {
    return [text(row.label), text(row.name), text(row.field_type), yes(row.required), text(row.transition_label)];
  }
  if (part === "triggers") {
    return [EVENT_LABELS[String(row.event)] || text(row.event), text(row.state_name)];
  }
  if (part === "actions") {
    const cfg = row.config as { message?: string } | null;
    const transition = transitions.find((item) => item.id === row.transition);
    const trigger = triggers.find((item) => item.id === row.trigger);
    return [
      ACTION_LABELS[String(row.action_type)] || text(row.action_type),
      text(transition?.label),
      text(trigger ? EVENT_LABELS[String(trigger.event)] || trigger.event : ""),
      text(cfg?.message),
    ];
  }
  if (part === "escalations") {
    const target = states.find((item) => item.id === row.escalate_to_state);
    return [text(row.name), text(row.escalation_hours), text(target?.name)];
  }
  const href = RECORD_HREF[String(row.module)];
  return [
    workflowTargetLabel(String(row.module || "")),
    href ? (
      <Link key="record" href={`${href}/${row.object_id}`}>
        {text(row.object_id)}
      </Link>
    ) : (
      text(row.object_id)
    ),
    text(row.state_name),
    formatDateTime(typeof row.entered_at === "string" ? row.entered_at : null),
  ];
}

function StateForm({
  initial,
  readOnly,
  onSubmit,
}: {
  initial?: Row | null;
  readOnly?: boolean;
  onSubmit: (body: Record<string, unknown>) => void;
}) {
  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [hours, setHours] = useState("");
  const [status, setStatus] = useState("");
  const [isInitial, setIsInitial] = useState(false);
  const [terminal, setTerminal] = useState(false);
  useEffect(() => {
    if (!initial) return;
    setName(textOrEmpty(initial.name));
    setCode(textOrEmpty(initial.code));
    setHours(initial.escalation_hours ? String(initial.escalation_hours) : "");
    setStatus(textOrEmpty(initial.document_status));
    setIsInitial(Boolean(initial.is_initial));
    setTerminal(Boolean(initial.is_terminal));
  }, [initial]);
  return (
    <Paper variant="outlined" sx={{ p: 2 }}>
      <Stack
        component="form"
        spacing={2}
        onSubmit={(e: FormEvent) => {
          e.preventDefault();
          onSubmit({
            name,
            code: code || name.toLowerCase().replace(/\s+/g, "_"),
            escalation_hours: hours ? Number(hours) : null,
            document_status: status,
            is_initial: isInitial,
            is_terminal: terminal,
          });
        }}
      >
        <TextField size="small" label="Name" value={name} onChange={(e) => setName(e.target.value)} required disabled={readOnly} />
        <TextField size="small" label="Code" value={code} onChange={(e) => setCode(e.target.value)} disabled={readOnly} />
        <TextField
          size="small"
          label="Escalate after hours"
          type="number"
          value={hours}
          onChange={(e) => setHours(e.target.value)}
          slotProps={{ htmlInput: { min: 0 } }}
          disabled={readOnly}
        />
        <TextField
          size="small"
          label="Record status"
          value={status}
          onChange={(e) => setStatus(e.target.value)}
          helperText="Used when this state is a document. Leave blank for other areas."
          disabled={readOnly}
        />
        <FormControlLabel control={<Checkbox checked={isInitial} onChange={(e) => setIsInitial(e.target.checked)} disabled={readOnly} />} label="Initial state" />
        <FormControlLabel control={<Checkbox checked={terminal} onChange={(e) => setTerminal(e.target.checked)} disabled={readOnly} />} label="Terminal state" />
        {readOnly ? null : (
          <Button type="submit" variant="contained" sx={{ alignSelf: "flex-start" }}>
            Save state
          </Button>
        )}
      </Stack>
    </Paper>
  );
}

function TransitionForm({
  initial,
  readOnly,
  states,
  roles,
  onSubmit,
}: {
  initial?: Row | null;
  readOnly?: boolean;
  states: Row[];
  roles: Row[];
  onSubmit: (body: Record<string, unknown>) => void;
}) {
  const [label, setLabel] = useState("");
  const [fromState, setFromState] = useState("");
  const [toState, setToState] = useState("");
  const [comment, setComment] = useState(false);
  const [signature, setSignature] = useState(false);
  const [sod, setSod] = useState(false);
  const [allowedRoles, setAllowedRoles] = useState<string[]>([]);
  const [events, setEvents] = useState<string[]>([]);
  useEffect(() => {
    if (!initial) return;
    setLabel(textOrEmpty(initial.label));
    setFromState(initial.from_state ? String(initial.from_state) : "");
    setToState(initial.to_state ? String(initial.to_state) : "");
    setComment(Boolean(initial.require_comment));
    setSignature(Boolean(initial.require_signature));
    setSod(Boolean(initial.block_self_approval));
    setAllowedRoles(Array.isArray(initial.allowed_roles) ? initial.allowed_roles.map(String) : []);
    setEvents(Array.isArray(initial.event_codes) ? initial.event_codes.map(String) : []);
  }, [initial]);
  return (
    <Paper variant="outlined" sx={{ p: 2 }}>
      <Stack
        component="form"
        spacing={2}
        onSubmit={(e: FormEvent) => {
          e.preventDefault();
          onSubmit({
            label,
            from_state: fromState,
            to_state: toState,
            require_comment: comment,
            require_signature: signature,
            block_self_approval: sod,
            allowed_roles: allowedRoles,
            events,
          });
        }}
      >
        <TextField
          size="small"
          label="Action name"
          value={label}
          onChange={(e) => setLabel(e.target.value)}
          required
          disabled={readOnly}
          helperText="Submit, Approve, Reject, or Post so journals, leave, orders, and payroll follow this step."
        />
        <TextField size="small" select label="From" value={fromState} onChange={(e) => setFromState(e.target.value)} required disabled={readOnly}>
          {states.map((row) => (
            <MenuItem key={row.id} value={String(row.id)}>
              {text(row.name)}
            </MenuItem>
          ))}
        </TextField>
        <TextField size="small" select label="To" value={toState} onChange={(e) => setToState(e.target.value)} required disabled={readOnly}>
          {states.map((row) => (
            <MenuItem key={row.id} value={String(row.id)}>
              {text(row.name)}
            </MenuItem>
          ))}
        </TextField>
        <TextField
          size="small"
          select
          label="Roles that may take this step"
          value={allowedRoles}
          onChange={(e) => setAllowedRoles(typeof e.target.value === "string" ? e.target.value.split(",") : e.target.value)}
          slotProps={{ select: { multiple: true } }}
          helperText="Leave empty to allow anyone who can change the record."
          disabled={readOnly}
        >
          {roles.map((row) => (
            <MenuItem key={row.id} value={String(row.id)}>
              {text(row.name)}
            </MenuItem>
          ))}
        </TextField>
        <TextField
          size="small"
          select
          label="Events that fire this step"
          value={events}
          onChange={(e) => setEvents(typeof e.target.value === "string" ? e.target.value.split(",") : e.target.value)}
          slotProps={{ select: { multiple: true } }}
          helperText="The step runs when the record is created, submitted, approved, rejected, or posted."
          disabled={readOnly}
        >
          {RECORD_EVENTS.map((row) => (
            <MenuItem key={row.value} value={row.value}>
              {row.label}
            </MenuItem>
          ))}
        </TextField>
        <FormControlLabel control={<Checkbox checked={comment} onChange={(e) => setComment(e.target.checked)} disabled={readOnly} />} label="Require a comment" />
        <FormControlLabel control={<Checkbox checked={signature} onChange={(e) => setSignature(e.target.checked)} disabled={readOnly} />} label="Require a signature" />
        <FormControlLabel control={<Checkbox checked={sod} onChange={(e) => setSod(e.target.checked)} disabled={readOnly} />} label="Block the previous actor" />
        {readOnly ? null : (
          <Button type="submit" variant="contained" sx={{ alignSelf: "flex-start" }}>
            Save transition
          </Button>
        )}
      </Stack>
    </Paper>
  );
}

function TriggerForm({
  initial,
  readOnly,
  states,
  onSubmit,
}: {
  initial?: Row | null;
  readOnly?: boolean;
  states: Row[];
  onSubmit: (body: Record<string, unknown>) => void;
}) {
  const [event, setEvent] = useState("on_enter");
  const [state, setState] = useState("");
  useEffect(() => {
    if (!initial) return;
    setEvent(textOrEmpty(initial.event) || "on_enter");
    setState(initial.state ? String(initial.state) : "");
  }, [initial]);
  return (
    <Paper variant="outlined" sx={{ p: 2 }}>
      <Stack
        component="form"
        spacing={2}
        onSubmit={(e: FormEvent) => {
          e.preventDefault();
          onSubmit({ event, state: state || null });
        }}
      >
        <TextField size="small" select label="When" value={event} onChange={(e) => setEvent(e.target.value)} disabled={readOnly}>
          <MenuItem value="on_enter">On enter</MenuItem>
          <MenuItem value="on_leave">On leave</MenuItem>
          <MenuItem value="on_overdue">On escalation</MenuItem>
        </TextField>
        <TextField size="small" select label="State" value={state} onChange={(e) => setState(e.target.value)} disabled={readOnly}>
          <MenuItem value="">Any state</MenuItem>
          {states.map((row) => (
            <MenuItem key={row.id} value={String(row.id)}>
              {text(row.name)}
            </MenuItem>
          ))}
        </TextField>
        {readOnly ? null : (
          <Button type="submit" variant="contained" sx={{ alignSelf: "flex-start" }}>
            Save trigger
          </Button>
        )}
      </Stack>
    </Paper>
  );
}

function ActionForm({
  initial,
  readOnly,
  transitions,
  triggers,
  onSubmit,
}: {
  initial?: Row | null;
  readOnly?: boolean;
  transitions: Row[];
  triggers: Row[];
  onSubmit: (body: Record<string, unknown>) => void;
}) {
  const [actionType, setActionType] = useState("notify");
  const [transition, setTransition] = useState("");
  const [trigger, setTrigger] = useState("");
  const [message, setMessage] = useState("");
  const [status, setStatus] = useState("");
  const [roleCode, setRoleCode] = useState("");
  const [title, setTitle] = useState("");
  useEffect(() => {
    if (!initial) return;
    const cfg = (initial.config || {}) as { message?: string; status?: string; role_code?: string; title?: string };
    setActionType(textOrEmpty(initial.action_type) || "notify");
    setTransition(initial.transition ? String(initial.transition) : "");
    setTrigger(initial.trigger ? String(initial.trigger) : "");
    setMessage(textOrEmpty(cfg.message));
    setStatus(textOrEmpty(cfg.status));
    setRoleCode(textOrEmpty(cfg.role_code));
    setTitle(textOrEmpty(cfg.title));
  }, [initial]);
  return (
    <Paper variant="outlined" sx={{ p: 2 }}>
      <Stack
        component="form"
        spacing={2}
        onSubmit={(e: FormEvent) => {
          e.preventDefault();
          if (!transition && !trigger) return;
          onSubmit({
            action_type: actionType,
            transition: transition || null,
            trigger: trigger || null,
            config: { message, status, role_code: roleCode, title },
          });
        }}
      >
        <TextField size="small" select label="Type" value={actionType} onChange={(e) => setActionType(e.target.value)} disabled={readOnly}>
          <MenuItem value="notify">Notify</MenuItem>
          <MenuItem value="notify_role">Notify a role</MenuItem>
          <MenuItem value="add_comment">Add comment</MenuItem>
          <MenuItem value="create_task">Create a task</MenuItem>
          <MenuItem value="set_status">Set status</MenuItem>
        </TextField>
        <TextField size="small" select label="On transition" value={transition} onChange={(e) => setTransition(e.target.value)} disabled={readOnly}>
          <MenuItem value="">None</MenuItem>
          {transitions.map((row) => (
            <MenuItem key={row.id} value={String(row.id)}>
              {text(row.label)}
            </MenuItem>
          ))}
        </TextField>
        <TextField size="small" select label="On trigger" value={trigger} onChange={(e) => setTrigger(e.target.value)} disabled={readOnly}>
          <MenuItem value="">None</MenuItem>
          {triggers.map((row) => (
            <MenuItem key={row.id} value={String(row.id)}>
              {EVENT_LABELS[String(row.event)] || text(row.event)}
            </MenuItem>
          ))}
        </TextField>
        <TextField size="small" label="Message" value={message} onChange={(e) => setMessage(e.target.value)} disabled={readOnly} />
        {actionType === "notify_role" || actionType === "create_task" ? (
          <TextField
            size="small"
            label="Role code"
            value={roleCode}
            onChange={(e) => setRoleCode(e.target.value)}
            helperText="The role code that should receive this notice or task."
            required={actionType === "notify_role"}
            disabled={readOnly}
          />
        ) : null}
        {actionType === "create_task" ? (
          <TextField
            size="small"
            label="Task title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            required
            disabled={readOnly}
          />
        ) : null}
        {actionType === "set_status" ? (
          <TextField size="small" label="Status" value={status} onChange={(e) => setStatus(e.target.value)} disabled={readOnly} />
        ) : null}
        {readOnly ? null : (
          <Button type="submit" variant="contained" sx={{ alignSelf: "flex-start" }} disabled={!transition && !trigger}>
            Save action
          </Button>
        )}
      </Stack>
    </Paper>
  );
}

function EscalationForm({
  states,
  childId,
  readOnly,
  onSubmit,
}: {
  states: Row[];
  childId: string;
  readOnly?: boolean;
  onSubmit: (body: Record<string, unknown>) => void;
}) {
  const current = states.find((row) => String(row.id) === childId);
  const [hours, setHours] = useState(current?.escalation_hours ? String(current.escalation_hours) : "");
  const [target, setTarget] = useState(current?.escalate_to_state ? String(current.escalate_to_state) : "");
  useEffect(() => {
    if (!current) return;
    setHours(current.escalation_hours ? String(current.escalation_hours) : "");
    setTarget(current.escalate_to_state ? String(current.escalate_to_state) : "");
  }, [current]);
  return (
    <Paper variant="outlined" sx={{ p: 2 }}>
      <Typography variant="subtitle1" sx={{ mb: 1 }}>
        {text(current?.name)}
      </Typography>
      <Stack
        component="form"
        spacing={2}
        onSubmit={(e: FormEvent) => {
          e.preventDefault();
          onSubmit({
            escalation_hours: hours ? Number(hours) : null,
            escalate_to_state: target || null,
          });
        }}
      >
        <TextField
          size="small"
          label="Escalate after hours"
          type="number"
          value={hours}
          onChange={(e) => setHours(e.target.value)}
          slotProps={{ htmlInput: { min: 0 } }}
          disabled={readOnly}
        />
        <TextField size="small" select label="Escalate to" value={target} onChange={(e) => setTarget(e.target.value)} disabled={readOnly}>
          <MenuItem value="">Stay in this state</MenuItem>
          {states
            .filter((row) => String(row.id) !== childId)
            .map((row) => (
              <MenuItem key={row.id} value={String(row.id)}>
                {text(row.name)}
              </MenuItem>
            ))}
        </TextField>
        {readOnly ? null : (
          <Button type="submit" variant="contained" sx={{ alignSelf: "flex-start" }}>
            Save escalation
          </Button>
        )}
      </Stack>
    </Paper>
  );
}

function EventForm({
  initial,
  readOnly,
  transitions,
  onSubmit,
}: {
  initial?: Row | null;
  readOnly?: boolean;
  transitions: Row[];
  onSubmit: (body: Record<string, unknown>) => void;
}) {
  const [transition, setTransition] = useState("");
  const [event, setEvent] = useState("record.submitted");
  useEffect(() => {
    if (!initial) return;
    setTransition(initial.transition ? String(initial.transition) : "");
    setEvent(textOrEmpty(initial.event) || "record.submitted");
  }, [initial]);
  return (
    <Paper variant="outlined" sx={{ p: 2 }}>
      <Stack
        component="form"
        spacing={2}
        onSubmit={(e: FormEvent) => {
          e.preventDefault();
          onSubmit({ transition, event });
        }}
      >
        <TextField size="small" select label="Transition" value={transition} onChange={(e) => setTransition(e.target.value)} required disabled={readOnly}>
          {transitions.map((row) => (
            <MenuItem key={row.id} value={String(row.id)}>
              {text(row.label)}
            </MenuItem>
          ))}
        </TextField>
        <TextField size="small" select label="Event" value={event} onChange={(e) => setEvent(e.target.value)} disabled={readOnly}>
          {RECORD_EVENTS.map((row) => (
            <MenuItem key={row.value} value={row.value}>
              {row.label}
            </MenuItem>
          ))}
        </TextField>
        {readOnly ? null : (
          <Button type="submit" variant="contained" sx={{ alignSelf: "flex-start" }}>
            Save event
          </Button>
        )}
      </Stack>
    </Paper>
  );
}

function FieldForm({
  initial,
  readOnly,
  transitions,
  onSubmit,
}: {
  initial?: Row | null;
  readOnly?: boolean;
  transitions: Row[];
  onSubmit: (body: Record<string, unknown>) => void;
}) {
  const [transition, setTransition] = useState("");
  const [label, setLabel] = useState("");
  const [name, setName] = useState("");
  const [fieldType, setFieldType] = useState("text");
  const [required, setRequired] = useState(false);
  useEffect(() => {
    if (!initial) return;
    setTransition(initial.transition ? String(initial.transition) : "");
    setLabel(textOrEmpty(initial.label));
    setName(textOrEmpty(initial.name));
    setFieldType(textOrEmpty(initial.field_type) || "text");
    setRequired(Boolean(initial.required));
  }, [initial]);
  return (
    <Paper variant="outlined" sx={{ p: 2 }}>
      <Stack
        component="form"
        spacing={2}
        onSubmit={(e: FormEvent) => {
          e.preventDefault();
          onSubmit({
            transition,
            label,
            name: name || label.toLowerCase().replace(/\s+/g, "_"),
            field_type: fieldType,
            required,
          });
        }}
      >
        <TextField size="small" select label="Transition" value={transition} onChange={(e) => setTransition(e.target.value)} required disabled={readOnly}>
          {transitions.map((row) => (
            <MenuItem key={row.id} value={String(row.id)}>
              {text(row.label)}
            </MenuItem>
          ))}
        </TextField>
        <TextField size="small" label="Label" value={label} onChange={(e) => setLabel(e.target.value)} required disabled={readOnly} />
        <TextField size="small" label="Name" value={name} onChange={(e) => setName(e.target.value)} disabled={readOnly} />
        <TextField size="small" select label="Type" value={fieldType} onChange={(e) => setFieldType(e.target.value)} disabled={readOnly}>
          <MenuItem value="text">Text</MenuItem>
          <MenuItem value="number">Number</MenuItem>
          <MenuItem value="date">Date</MenuItem>
        </TextField>
        <FormControlLabel control={<Checkbox checked={required} onChange={(e) => setRequired(e.target.checked)} disabled={readOnly} />} label="Required" />
        {readOnly ? null : (
          <Button type="submit" variant="contained" sx={{ alignSelf: "flex-start" }}>
            Save field
          </Button>
        )}
      </Stack>
    </Paper>
  );
}

function RecordView({ row }: { row: Row }) {
  const href = RECORD_HREF[String(row.module || "")];
  return (
    <Paper variant="outlined" sx={{ p: 2 }}>
      <Stack spacing={1}>
        <Typography>Area: {workflowTargetLabel(String(row.module || ""))}</Typography>
        <Typography>Record: {text(row.object_id)}</Typography>
        <Typography>State: {text(row.state_name)}</Typography>
        <Typography>
          Entered: {formatDateTime(typeof row.entered_at === "string" ? row.entered_at : null)}
        </Typography>
        {href ? (
          <Button component={Link} href={`${href}/${row.object_id}`} variant="contained" sx={{ alignSelf: "flex-start" }}>
            Open record
          </Button>
        ) : null}
      </Stack>
    </Paper>
  );
}
