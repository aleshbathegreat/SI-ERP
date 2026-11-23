"use client";

import { Button } from "@mui/material";
import LockIcon from "@mui/icons-material/Lock";
import LockOpenIcon from "@mui/icons-material/LockOpen";
import { useRecordAction } from "@/hooks/useRecordAction";
import { usePermissions } from "@/hooks/usePermissions";
import type { RowActionItem } from "@/components/crud/RowActionsMenu";

const MODULE = "finance.journals";

type Row = { id: number; is_locked?: boolean };

export function usePeriodActions() {
  const { run, busyKey, busy } = useRecordAction();
  const { canChange } = usePermissions();

  const toggle = (row: Row, reload?: () => void) => {
    const action = row.is_locked ? "unlock" : "lock";
    return run(`${action}-${row.id}`, `/finance/periods/${row.id}/${action}/`, {
      success: row.is_locked ? "Period unlocked" : "Period locked",
      onDone: () => reload?.(),
    });
  };

  const rowActions = (row: Row, reload: () => void): RowActionItem[] => {
    if (!canChange(MODULE)) return [];
    const action = row.is_locked ? "unlock" : "lock";
    return [
      {
        key: action,
        label: row.is_locked ? "Unlock" : "Lock",
        icon: row.is_locked ? (
          <LockOpenIcon fontSize="small" />
        ) : (
          <LockIcon fontSize="small" />
        ),
        disabled: busy,
        onClick: () => void toggle(row, reload),
      },
    ];
  };

  const actionButtons = (row: Row, reload: () => void) => {
    if (!canChange(MODULE)) return null;
    const action = row.is_locked ? "unlock" : "lock";
    return (
      <Button
        variant="outlined"
        startIcon={row.is_locked ? <LockOpenIcon /> : <LockIcon />}
        disabled={busy}
        onClick={() => void toggle(row, reload)}
      >
        {busyKey === `${action}-${row.id}`
          ? row.is_locked
            ? "Unlocking…"
            : "Locking…"
          : row.is_locked
            ? "Unlock"
            : "Lock"}
      </Button>
    );
  };

  return { rowActions, actionButtons };
}
