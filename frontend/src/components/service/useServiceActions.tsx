"use client";

import { Button } from "@mui/material";
import PersonAddAltOutlinedIcon from "@mui/icons-material/PersonAddAltOutlined";
import CheckCircleOutlinedIcon from "@mui/icons-material/CheckCircleOutlined";
import LockOutlinedIcon from "@mui/icons-material/LockOutlined";
import ReplayIcon from "@mui/icons-material/Replay";
import { useRecordAction } from "@/hooks/useRecordAction";
import { usePermissions } from "@/hooks/usePermissions";
import { useAppSelector } from "@/store/hooks";
import type { RowActionItem } from "@/components/crud/RowActionsMenu";

const MODULE = "service.cases";
const API = "/service/cases/";

type Row = Record<string, unknown> & { id: number };
type CaseAction = "assign" | "resolve" | "close" | "reopen";

const SUCCESS: Record<CaseAction, string> = {
  assign: "Case assigned",
  resolve: "Case resolved",
  close: "Case closed",
  reopen: "Case reopened",
};

export function useServiceActions() {
  const { run, busyKey, busy } = useRecordAction();
  const { canChange } = usePermissions();
  const userId = useAppSelector((s) => s.auth.user?.id);

  const act = (id: number, action: CaseAction, reload?: () => void) =>
    run(`${action}-${id}`, `${API}${id}/${action}/`, {
      body: action === "assign" ? { assigned_to: userId } : undefined,
      success: SUCCESS[action],
      onDone: () => reload?.(),
    });

  const available = (status: unknown) => {
    const ok = canChange(MODULE);
    const s = String(status ?? "");
    return {
      assign: ok && !!userId && s !== "closed",
      resolve: ok && s !== "resolved" && s !== "closed",
      close: ok && s !== "closed",
      reopen: ok && (s === "resolved" || s === "closed"),
    };
  };

  const rowActions = (row: Row, reload: () => void): RowActionItem[] => {
    const a = available(row.status);
    const out: RowActionItem[] = [];
    if (a.assign)
      out.push({
        key: "assign",
        label: "Assign to me",
        icon: <PersonAddAltOutlinedIcon fontSize="small" />,
        disabled: busy,
        onClick: () => void act(row.id, "assign", reload),
      });
    if (a.resolve)
      out.push({
        key: "resolve",
        label: "Resolve",
        icon: <CheckCircleOutlinedIcon fontSize="small" />,
        disabled: busy,
        onClick: () => void act(row.id, "resolve", reload),
      });
    if (a.close)
      out.push({
        key: "close",
        label: "Close",
        icon: <LockOutlinedIcon fontSize="small" />,
        disabled: busy,
        onClick: () => void act(row.id, "close", reload),
      });
    if (a.reopen)
      out.push({
        key: "reopen",
        label: "Reopen",
        icon: <ReplayIcon fontSize="small" />,
        disabled: busy,
        onClick: () => void act(row.id, "reopen", reload),
      });
    return out;
  };

  const actionButtons = (id: number, row: Row, reload: () => void) => {
    const a = available(row.status);
    const btn = (
      action: CaseAction,
      label: string,
      icon: React.ReactNode,
      variant: "contained" | "outlined" = "outlined"
    ) => (
      <Button
        key={action}
        variant={variant}
        startIcon={icon}
        disabled={busy}
        onClick={() => void act(id, action, reload)}
      >
        {busyKey === `${action}-${id}` ? "Working…" : label}
      </Button>
    );
    return (
      <>
        {a.assign ? btn("assign", "Assign to me", <PersonAddAltOutlinedIcon />) : null}
        {a.resolve ? btn("resolve", "Resolve", <CheckCircleOutlinedIcon />, "contained") : null}
        {a.close ? btn("close", "Close", <LockOutlinedIcon />) : null}
        {a.reopen ? btn("reopen", "Reopen", <ReplayIcon />) : null}
      </>
    );
  };

  return { rowActions, actionButtons };
}
