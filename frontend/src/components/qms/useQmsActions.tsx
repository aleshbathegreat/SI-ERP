"use client";

import { useRouter } from "next/navigation";
import { Button } from "@mui/material";
import LockOutlinedIcon from "@mui/icons-material/LockOutlined";
import TaskAltIcon from "@mui/icons-material/TaskAlt";
import ReportProblemOutlinedIcon from "@mui/icons-material/ReportProblemOutlined";
import { useRecordAction } from "@/hooks/useRecordAction";
import { usePermissions } from "@/hooks/usePermissions";
import type { RowActionItem } from "@/components/crud/RowActionsMenu";

type Row = Record<string, unknown> & { id: number };
type NcrResult = { ncr: number; ncr_no: string; created: boolean };

const DISPOSITIONS = ["rework", "scrap", "use_as_is", "return_vendor"];

export function useQmsActions() {
  const router = useRouter();
  const { run, busyKey, busy } = useRecordAction();
  const { canAdd, canChange } = usePermissions();

  const closeNcr = (row: Row, reload?: () => void) => {
    let disposition = String(row.disposition || "");
    if (!DISPOSITIONS.includes(disposition)) {
      const picked = window.prompt(
        `Disposition required to close ${String(row.ncr_no ?? "NCR")}:\n${DISPOSITIONS.join(" / ")}`,
        "rework"
      );
      if (!picked) return Promise.resolve(null);
      disposition = picked.trim();
    }
    return run(`close-${row.id}`, `/qms/ncrs/${row.id}/close/`, {
      body: { disposition },
      success: "NCR closed",
      onDone: () => reload?.(),
    });
  };

  const completeCapa = (id: number, reload?: () => void) =>
    run(`complete-${id}`, `/qms/capas/${id}/complete/`, {
      success: "CAPA completed",
      onDone: () => reload?.(),
    });

  const raiseNcr = (id: number) =>
    run<NcrResult>(`ncr-${id}`, `/qms/inspections/${id}/create-ncr/`, {
      success: (d) =>
        d.created ? `NCR ${d.ncr_no} created` : `Opening existing NCR ${d.ncr_no}`,
      onDone: (d) => router.push(`/qms/ncrs/${d.ncr}`),
    });

  const canRaise = (row: Row) =>
    canAdd("qms.ncrs") && canAdd("qms.inspections") && row.result !== "pass";

  const ncrRowActions = (row: Row, reload: () => void): RowActionItem[] =>
    canChange("qms.ncrs") && row.status !== "closed"
      ? [
          {
            key: "close",
            label: "Close NCR",
            icon: <LockOutlinedIcon fontSize="small" />,
            disabled: busy,
            onClick: () => void closeNcr(row, reload),
          },
        ]
      : [];

  const capaRowActions = (row: Row, reload: () => void): RowActionItem[] =>
    canChange("qms.capas") && row.status !== "done"
      ? [
          {
            key: "complete",
            label: "Complete CAPA",
            icon: <TaskAltIcon fontSize="small" />,
            disabled: busy,
            onClick: () => void completeCapa(row.id, reload),
          },
        ]
      : [];

  const inspectionRowActions = (row: Row): RowActionItem[] =>
    canRaise(row)
      ? [
          {
            key: "raise-ncr",
            label: "Raise NCR",
            icon: <ReportProblemOutlinedIcon fontSize="small" />,
            disabled: busy,
            onClick: () => void raiseNcr(row.id),
          },
        ]
      : [];

  const closeNcrButton = (row: Row, reload: () => void) =>
    canChange("qms.ncrs") && row.status !== "closed" ? (
      <Button
        variant="contained"
        color="secondary"
        startIcon={<LockOutlinedIcon />}
        disabled={busy}
        onClick={() => void closeNcr(row, reload)}
      >
        {busyKey === `close-${row.id}` ? "Closing…" : "Close NCR"}
      </Button>
    ) : null;

  const completeCapaButton = (row: Row, reload: () => void) =>
    canChange("qms.capas") && row.status !== "done" ? (
      <Button
        variant="contained"
        color="secondary"
        startIcon={<TaskAltIcon />}
        disabled={busy}
        onClick={() => void completeCapa(row.id, reload)}
      >
        {busyKey === `complete-${row.id}` ? "Completing…" : "Complete CAPA"}
      </Button>
    ) : null;

  const raiseNcrButton = (row: Row) =>
    canRaise(row) ? (
      <Button
        variant="contained"
        color="secondary"
        startIcon={<ReportProblemOutlinedIcon />}
        disabled={busy}
        onClick={() => void raiseNcr(row.id)}
      >
        {busyKey === `ncr-${row.id}` ? "Creating…" : "Raise NCR"}
      </Button>
    ) : null;

  return {
    ncrRowActions,
    capaRowActions,
    inspectionRowActions,
    closeNcrButton,
    completeCapaButton,
    raiseNcrButton,
  };
}
