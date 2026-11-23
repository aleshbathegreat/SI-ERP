"use client";

import { Button } from "@mui/material";
import SendOutlinedIcon from "@mui/icons-material/SendOutlined";
import CheckCircleOutlinedIcon from "@mui/icons-material/CheckCircleOutlined";
import UndoIcon from "@mui/icons-material/Undo";
import { useRecordAction } from "@/hooks/useRecordAction";
import { usePermissions } from "@/hooks/usePermissions";
import type { RowActionItem } from "@/components/crud/RowActionsMenu";

const MODULE = "projects.timesheets";
const API = "/projects/timesheets/";

type Row = Record<string, unknown> & { id: number };

export function useTimesheetActions() {
  const { run, busy } = useRecordAction();
  const { canAdd, canChange } = usePermissions();

  const act = (
    id: number,
    action: "submit" | "approve" | "reject",
    reload: () => void
  ) =>
    run(`${action}-${id}`, `${API}${id}/${action}/`, {
      success:
        action === "submit"
          ? "Time entry submitted"
          : action === "approve"
            ? "Time entry approved"
            : "Time entry returned to draft",
      onDone: reload,
    });

  const available = (status: unknown) => ({
    submit: status === "draft" && canAdd(MODULE),
    approve: status === "submitted" && canChange(MODULE),
    reject: status === "submitted" && canChange(MODULE),
  });

  const rowActions = (row: Row, reload: () => void): RowActionItem[] => {
    const a = available(row.status);
    const out: RowActionItem[] = [];
    if (a.submit)
      out.push({
        key: "submit",
        label: "Submit",
        icon: <SendOutlinedIcon fontSize="small" />,
        disabled: busy,
        onClick: () => void act(row.id, "submit", reload),
      });
    if (a.approve)
      out.push({
        key: "approve",
        label: "Approve",
        icon: <CheckCircleOutlinedIcon fontSize="small" />,
        disabled: busy,
        onClick: () => void act(row.id, "approve", reload),
      });
    if (a.reject)
      out.push({
        key: "reject",
        label: "Return to draft",
        icon: <UndoIcon fontSize="small" />,
        disabled: busy,
        onClick: () => void act(row.id, "reject", reload),
      });
    return out;
  };

  const actionButtons = (id: number, status: unknown, reload: () => void) => {
    const a = available(status);
    return (
      <>
        {a.submit ? (
          <Button
            variant="contained"
            color="secondary"
            startIcon={<SendOutlinedIcon />}
            disabled={busy}
            onClick={() => void act(id, "submit", reload)}
          >
            Submit
          </Button>
        ) : null}
        {a.approve ? (
          <Button
            variant="contained"
            color="success"
            startIcon={<CheckCircleOutlinedIcon />}
            disabled={busy}
            onClick={() => void act(id, "approve", reload)}
          >
            Approve
          </Button>
        ) : null}
        {a.reject ? (
          <Button
            variant="outlined"
            startIcon={<UndoIcon />}
            disabled={busy}
            onClick={() => void act(id, "reject", reload)}
          >
            Return to draft
          </Button>
        ) : null}
      </>
    );
  };

  return { rowActions, actionButtons };
}
