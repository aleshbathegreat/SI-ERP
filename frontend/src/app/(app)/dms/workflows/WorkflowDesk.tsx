"use client";

import { FormEvent, useState } from "react";
import { Button, MenuItem, Paper, Stack, TextField, Typography } from "@mui/material";
import { useSnackbar } from "notistack";
import api from "@/lib/api";
import { errorSnackbarOpts, getApiErrorMessage } from "@/lib/apiError";
import { WorkflowPreviewData } from "../documents/WorkflowPreview";
import { WorkflowMap } from "./WorkflowMap";

type StateRow = { id: number; name: string };
type TransitionRow = { id: number; label: string };

export function WorkflowDesk({
  id,
  form,
  onDone,
}: {
  id: string;
  form: Record<string, unknown>;
  onDone: () => void;
}) {
  const { enqueueSnackbar } = useSnackbar();
  const preview = (form.preview as WorkflowPreviewData) || null;
  const states = (form.states as StateRow[]) || [];
  const transitions = (form.transitions as TransitionRow[]) || [];
  const [stateName, setStateName] = useState("");
  const [stateCode, setStateCode] = useState("");
  const [hours, setHours] = useState("");
  const [fromState, setFromState] = useState("");
  const [toState, setToState] = useState("");
  const [label, setLabel] = useState("");
  const [requireSignature, setRequireSignature] = useState(false);
  const [transitionId, setTransitionId] = useState("");
  const [actionType, setActionType] = useState("notify");
  const [message, setMessage] = useState("");
  const [triggerEvent, setTriggerEvent] = useState("on_enter");
  const [triggerState, setTriggerState] = useState("");

  const post = async (path: string, body: unknown, ok: string) => {
    try {
      await api.post(path, body);
      enqueueSnackbar(ok, { variant: "success" });
      onDone();
    } catch (e) {
      enqueueSnackbar(getApiErrorMessage(e, "Save failed"), errorSnackbarOpts);
    }
  };

  return (
    <Stack spacing={2} sx={{ mt: 2 }}>
      <WorkflowMap preview={preview} title={String(form.name || "Workflow")} />
      <Paper variant="outlined" sx={{ p: 2 }}>
        <Typography variant="subtitle1" sx={{ mb: 1 }}>
          Add state
        </Typography>
        <Stack
          component="form"
          direction="row"
          spacing={1}
          onSubmit={(e: FormEvent) => {
            e.preventDefault();
            void post(
              "/dms/workflow-states/",
              {
                workflow: id,
                name: stateName,
                code: stateCode || stateName.toLowerCase().replace(/\s+/g, "_"),
                escalation_hours: hours ? Number(hours) : null,
                document_status: "",
              },
              "State added"
            );
          }}
        >
          <TextField size="small" label="Name" value={stateName} onChange={(e) => setStateName(e.target.value)} required />
          <TextField size="small" label="Code" value={stateCode} onChange={(e) => setStateCode(e.target.value)} />
          <TextField size="small" label="Escalate after hours" type="number" value={hours} onChange={(e) => setHours(e.target.value)} />
          <Button type="submit" variant="outlined">
            Add state
          </Button>
        </Stack>
      </Paper>
      <Paper variant="outlined" sx={{ p: 2 }}>
        <Typography variant="subtitle1" sx={{ mb: 1 }}>
          Add transition
        </Typography>
        <Stack
          component="form"
          direction="row"
          spacing={1}
          flexWrap="wrap"
          useFlexGap
          onSubmit={(e: FormEvent) => {
            e.preventDefault();
            void post(
              "/dms/workflow-transitions/",
              {
                workflow: id,
                from_state: fromState,
                to_state: toState,
                label,
                require_signature: requireSignature,
              },
              "Transition added"
            );
          }}
        >
          <TextField select size="small" label="From" value={fromState} onChange={(e) => setFromState(e.target.value)} sx={{ minWidth: 140 }}>
            {states.map((state) => (
              <MenuItem key={state.id} value={state.id}>
                {state.name}
              </MenuItem>
            ))}
          </TextField>
          <TextField select size="small" label="To" value={toState} onChange={(e) => setToState(e.target.value)} sx={{ minWidth: 140 }}>
            {states.map((state) => (
              <MenuItem key={state.id} value={state.id}>
                {state.name}
              </MenuItem>
            ))}
          </TextField>
          <TextField size="small" label="Action label" value={label} onChange={(e) => setLabel(e.target.value)} required />
          <TextField
            select
            size="small"
            label="Signature"
            value={requireSignature ? "yes" : "no"}
            onChange={(e) => setRequireSignature(e.target.value === "yes")}
          >
            <MenuItem value="no">Not required</MenuItem>
            <MenuItem value="yes">Required</MenuItem>
          </TextField>
          <Button type="submit" variant="outlined" disabled={!fromState || !toState}>
            Add transition
          </Button>
        </Stack>
      </Paper>
      <Paper variant="outlined" sx={{ p: 2 }}>
        <Typography variant="subtitle1" sx={{ mb: 1 }}>
          Add action or trigger
        </Typography>
        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
          <TextField select size="small" label="Transition" value={transitionId} onChange={(e) => setTransitionId(e.target.value)} sx={{ minWidth: 160 }}>
            {transitions.map((row) => (
              <MenuItem key={row.id} value={row.id}>
                {row.label}
              </MenuItem>
            ))}
          </TextField>
          <TextField select size="small" label="Action" value={actionType} onChange={(e) => setActionType(e.target.value)}>
            <MenuItem value="notify">Notify</MenuItem>
            <MenuItem value="add_comment">Comment</MenuItem>
            <MenuItem value="set_status">Set status</MenuItem>
          </TextField>
          <TextField size="small" label="Message or status" value={message} onChange={(e) => setMessage(e.target.value)} />
          <Button
            variant="outlined"
            disabled={!transitionId}
            onClick={() =>
              void post(
                "/dms/workflow-actions/",
                {
                  workflow: id,
                  transition: transitionId,
                  action_type: actionType,
                  config: actionType === "set_status" ? { status: message } : { message },
                },
                "Action added"
              )
            }
          >
            Add action
          </Button>
          <TextField select size="small" label="Trigger" value={triggerEvent} onChange={(e) => setTriggerEvent(e.target.value)}>
            <MenuItem value="on_enter">On enter</MenuItem>
            <MenuItem value="on_leave">On leave</MenuItem>
            <MenuItem value="on_overdue">On escalation</MenuItem>
          </TextField>
          <TextField select size="small" label="State" value={triggerState} onChange={(e) => setTriggerState(e.target.value)} sx={{ minWidth: 140 }}>
            {states.map((state) => (
              <MenuItem key={state.id} value={state.id}>
                {state.name}
              </MenuItem>
            ))}
          </TextField>
          <Button
            variant="outlined"
            disabled={!triggerState}
            onClick={() =>
              void post(
                "/dms/workflow-triggers/",
                { workflow: id, event: triggerEvent, state: triggerState },
                "Trigger added"
              )
            }
          >
            Add trigger
          </Button>
        </Stack>
      </Paper>
    </Stack>
  );
}
