"use client";

import { Button } from "@mui/material";
import PlayArrowOutlinedIcon from "@mui/icons-material/PlayArrowOutlined";
import CheckCircleOutlinedIcon from "@mui/icons-material/CheckCircleOutlined";
import CancelOutlinedIcon from "@mui/icons-material/CancelOutlined";
import { useRecordAction } from "@/hooks/useRecordAction";
import { usePermissions } from "@/hooks/usePermissions";
import type { RowActionItem } from "@/components/crud/RowActionsMenu";

const MODULE = "finance.maintenance";
const MWO_API = "/finance/maintenance-orders/";
const PM_API = "/finance/pm-schedules/";

type Row = Record<string, unknown> & { id: number };
type MwoAction = "start" | "complete" | "cancel";

type GenerateResult = { created: number; skipped: number };

export function useMaintenanceActions() {
  const { run, busyKey, busy } = useRecordAction();
  const { canAdd, canChange } = usePermissions();

  const act = (id: number, action: MwoAction, reload?: () => void) =>
    run(`${action}-${id}`, `${MWO_API}${id}/${action}/`, {
      success:
        action === "start"
          ? "Work order started"
          : action === "complete"
            ? "Work order completed"
            : "Work order cancelled",
      onDone: () => reload?.(),
    });

  const available = (status: unknown) => {
    const ok = canChange(MODULE);
    const s = String(status ?? "");
    const live = s === "open" || s === "scheduled" || s === "in_progress";
    return {
      start: ok && (s === "open" || s === "scheduled"),
      complete: ok && live,
      cancel: ok && live,
    };
  };

  const rowActions = (row: Row, reload: () => void): RowActionItem[] => {
    const a = available(row.status);
    const out: RowActionItem[] = [];
    if (a.start)
      out.push({
        key: "start",
        label: "Start",
        icon: <PlayArrowOutlinedIcon fontSize="small" />,
        disabled: busy,
        onClick: () => void act(row.id, "start", reload),
      });
    if (a.complete)
      out.push({
        key: "complete",
        label: "Complete",
        icon: <CheckCircleOutlinedIcon fontSize="small" />,
        disabled: busy,
        onClick: () => void act(row.id, "complete", reload),
      });
    if (a.cancel)
      out.push({
        key: "cancel",
        label: "Cancel",
        icon: <CancelOutlinedIcon fontSize="small" />,
        disabled: busy,
        danger: true,
        onClick: () => void act(row.id, "cancel", reload),
      });
    return out;
  };

  const actionButtons = (id: number, row: Row, reload: () => void) => {
    const a = available(row.status);
    return (
      <>
        {a.start ? (
          <Button
            variant="outlined"
            startIcon={<PlayArrowOutlinedIcon />}
            disabled={busy}
            onClick={() => void act(id, "start", reload)}
          >
            {busyKey === `start-${id}` ? "Starting…" : "Start"}
          </Button>
        ) : null}
        {a.complete ? (
          <Button
            variant="contained"
            color="secondary"
            startIcon={<CheckCircleOutlinedIcon />}
            disabled={busy}
            onClick={() => void act(id, "complete", reload)}
          >
            {busyKey === `complete-${id}` ? "Completing…" : "Complete"}
          </Button>
        ) : null}
        {a.cancel ? (
          <Button
            variant="outlined"
            color="error"
            startIcon={<CancelOutlinedIcon />}
            disabled={busy}
            onClick={() => void act(id, "cancel", reload)}
          >
            Cancel
          </Button>
        ) : null}
      </>
    );
  };

  const generateDue = (reload?: () => void) =>
    run<GenerateResult>("generate-due", `${PM_API}generate-due/`, {
      success: (d) =>
        d.created
          ? `${d.created} work order(s) generated`
          : "No schedules are due (or work orders already open)",
      onDone: () => reload?.(),
    });

  const generateDueButton = (reload?: () => void) =>
    canAdd(MODULE) ? (
      <Button
        variant="contained"
        color="secondary"
        disabled={busy}
        onClick={() => void generateDue(reload)}
      >
        {busyKey === "generate-due" ? "Generating…" : "Generate due work orders"}
      </Button>
    ) : null;

  return { rowActions, actionButtons, generateDue, generateDueButton };
}
