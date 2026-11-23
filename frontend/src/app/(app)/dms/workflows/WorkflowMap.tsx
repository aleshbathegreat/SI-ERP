"use client";

import {
  Chip,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";
import { WorkflowPreview, WorkflowPreviewData } from "../documents/WorkflowPreview";

type Action = { action_type: string; config?: { status?: string; message?: string } };

const EVENTS: Record<string, string> = {
  on_enter: "When the document enters",
  on_leave: "When the document leaves",
  on_overdue: "When the state is overdue",
};

const ACTIONS: Record<string, string> = {
  set_status: "Set document status",
  notify: "Notify",
  notify_role: "Notify a role",
  add_comment: "Add a comment",
  create_task: "Create a task",
};

function actionText(action: Action) {
  const name = ACTIONS[action.action_type] || action.action_type.replaceAll("_", " ");
  if (action.config?.status) return `${name}: ${action.config.status}`;
  if (action.config?.message) return `${name}: ${action.config.message}`;
  return name;
}

function rules(row: {
  require_signature?: boolean;
  require_comment?: boolean;
  block_self_approval?: boolean;
}) {
  const parts = [
    row.require_signature ? "Signature required" : "",
    row.require_comment ? "Comment required" : "",
    row.block_self_approval ? "Cannot approve your own document" : "",
  ].filter(Boolean);
  return parts.length ? parts.join(", ") : "—";
}

export function WorkflowMap({ preview, title }: { preview?: WorkflowPreviewData | null; title?: string }) {
  const states = preview?.states || [];
  const transitions = preview?.transitions || [];
  const triggers = preview?.triggers || [];

  return (
    <Stack spacing={2.5} sx={{ mt: 1 }}>
      <WorkflowPreview preview={preview} title={title} />
      <Stack spacing={1} sx={{ overflowX: "auto" }}>
        <Typography variant="subtitle1">States</Typography>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>State</TableCell>
              <TableCell>Kind</TableCell>
              <TableCell>Document status</TableCell>
              <TableCell>Escalation</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {states.map((state) => (
              <TableRow key={state.id}>
                <TableCell>{state.name}</TableCell>
                <TableCell>{state.is_initial ? "Start" : state.is_terminal ? "End" : "In progress"}</TableCell>
                <TableCell>{state.document_status || "—"}</TableCell>
                <TableCell>{state.escalation_hours ? `After ${state.escalation_hours} hours` : "—"}</TableCell>
              </TableRow>
            ))}
            {!states.length ? (
              <TableRow>
                <TableCell colSpan={4}>No states yet.</TableCell>
              </TableRow>
            ) : null}
          </TableBody>
        </Table>
      </Stack>
      <Stack spacing={1} sx={{ overflowX: "auto" }}>
        <Typography variant="subtitle1">Transitions</Typography>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Transition</TableCell>
              <TableCell>Origin</TableCell>
              <TableCell>Destination</TableCell>
              <TableCell>Rules</TableCell>
              <TableCell>Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {transitions.map((row) => (
              <TableRow key={row.id}>
                <TableCell>{row.label}</TableCell>
                <TableCell>{row.from_name}</TableCell>
                <TableCell>{row.to_name}</TableCell>
                <TableCell>{rules(row)}</TableCell>
                <TableCell>
                  {(row.actions || []).length
                    ? (row.actions || []).map((action) => actionText(action as Action)).join(", ")
                    : "—"}
                </TableCell>
              </TableRow>
            ))}
            {!transitions.length ? (
              <TableRow>
                <TableCell colSpan={5}>No transitions yet.</TableCell>
              </TableRow>
            ) : null}
          </TableBody>
        </Table>
      </Stack>
      <Stack spacing={1} sx={{ overflowX: "auto" }}>
        <Typography variant="subtitle1">Triggers</Typography>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>When</TableCell>
              <TableCell>State</TableCell>
              <TableCell>Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {triggers.map((trigger) => (
              <TableRow key={trigger.id}>
                <TableCell>{EVENTS[trigger.event] || trigger.event}</TableCell>
                <TableCell>{trigger.state_name || "Any state"}</TableCell>
                <TableCell>
                  {(trigger.actions || []).length ? (
                    <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap>
                      {(trigger.actions || []).map((action, index) => (
                        <Chip
                          key={`${trigger.id}-${index}`}
                          size="small"
                          variant="outlined"
                          label={actionText(action as Action)}
                        />
                      ))}
                    </Stack>
                  ) : (
                    "—"
                  )}
                </TableCell>
              </TableRow>
            ))}
            {!triggers.length ? (
              <TableRow>
                <TableCell colSpan={3}>No triggers yet.</TableCell>
              </TableRow>
            ) : null}
          </TableBody>
        </Table>
      </Stack>
    </Stack>
  );
}
