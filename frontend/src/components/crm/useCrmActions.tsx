"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@mui/material";
import SwapHorizIcon from "@mui/icons-material/SwapHoriz";
import RequestQuoteOutlinedIcon from "@mui/icons-material/RequestQuoteOutlined";
import { useRecordAction } from "@/hooks/useRecordAction";
import { usePermissions } from "@/hooks/usePermissions";
import type { RowActionItem } from "@/components/crud/RowActionsMenu";
import LostStageDialog from "@/components/crm/LostStageDialog";

type ConvertResult = {
  created: boolean;
  customer_id: number | null;
  customer_code: string;
  opportunity_id: number | null;
  href: string;
};

type QuoteResult = {
  created: boolean;
  quotation_id: number;
  quote_no: string;
  href: string;
};

type Row = Record<string, unknown>;

export const canConvertLead = (row: Row) =>
  row.status !== "converted" && row.status !== "lost";

export const canQuoteOpportunity = (row: Row) => row.stage !== "lost";

export function useCrmActions() {
  const router = useRouter();
  const { run, busyKey, busy } = useRecordAction();
  const { canAdd, canChange } = usePermissions();
  const [lost, setLost] = useState<{ id: number; onDone?: () => void } | null>(null);

  const convertLead = (id: number) =>
    run<ConvertResult>(`convert-${id}`, `/crm/leads/${id}/convert/`, {
      success: (d) =>
        d.created
          ? `Lead converted · customer ${d.customer_code}`
          : "Lead was already converted",
      onDone: (d) => d.href && router.push(d.href),
    });

  const createQuote = (id: number) =>
    run<QuoteResult>(`quote-${id}`, `/crm/opportunities/${id}/create-quote/`, {
      success: (d) =>
        d.created ? `Draft quote ${d.quote_no} created` : `Opening draft quote ${d.quote_no}`,
      onDone: (d) => d.href && router.push(d.href),
    });

  const moveStage = (id: number, stage: string, closeReason?: string, onDone?: () => void) =>
    run(`move-${id}-${stage}`, `/crm/opportunities/${id}/move/`, {
      body: closeReason ? { stage, close_reason: closeReason } : { stage },
      success: stage === "won" ? "Deal marked won" : stage === "lost" ? "Deal marked lost" : "Stage updated",
      onDone: () => onDone?.(),
    });

  const askLost = (id: number, onDone?: () => void) => setLost({ id, onDone });

  const completeActivity = (id: number, onDone?: () => void) =>
    run(`done-${id}`, `/crm/activities/${id}/complete/`, {
      success: "Activity marked done",
      onDone: () => onDone?.(),
    });

  const leadRowActions = (row: Row & { id: number }): RowActionItem[] =>
    canAdd("crm.leads") && canConvertLead(row)
      ? [
          {
            key: "convert",
            label: "Convert to customer + opportunity",
            icon: <SwapHorizIcon fontSize="small" />,
            disabled: busy,
            onClick: () => void convertLead(row.id),
          },
        ]
      : [];

  const opportunityRowActions = (
    row: Row & { id: number },
    ctx?: { reload: () => void }
  ): RowActionItem[] => {
    const items: RowActionItem[] = [];
    if (canAdd("sales.quotes") && canQuoteOpportunity(row)) {
      items.push({
        key: "create-quote",
        label: "Create quote",
        icon: <RequestQuoteOutlinedIcon fontSize="small" />,
        disabled: busy,
        onClick: () => void createQuote(row.id),
      });
    }
    if (canChange("crm.opportunities") && row.stage !== "won") {
      items.push({
        key: "mark-won",
        label: "Mark won",
        disabled: busy,
        onClick: () => void moveStage(row.id, "won", undefined, ctx?.reload),
      });
    }
    if (canChange("crm.opportunities") && row.stage !== "lost") {
      items.push({
        key: "mark-lost",
        label: "Mark lost",
        danger: true,
        dividerBefore: true,
        disabled: busy,
        onClick: () => askLost(row.id, ctx?.reload),
      });
    }
    return items;
  };

  const activityRowActions = (
    row: Row & { id: number },
    ctx?: { reload: () => void }
  ): RowActionItem[] =>
    !row.done && canChange("crm.activities")
      ? [
          {
            key: "done",
            label: "Mark done",
            disabled: busy,
            onClick: () => void completeActivity(row.id, ctx?.reload),
          },
        ]
      : [];

  const convertLeadButton = (id: number, row: Row) =>
    canAdd("crm.leads") && canConvertLead(row) ? (
      <Button
        variant="contained"
        color="secondary"
        startIcon={<SwapHorizIcon />}
        disabled={busy}
        onClick={() => void convertLead(id)}
      >
        {busyKey === `convert-${id}` ? "Converting…" : "Convert lead"}
      </Button>
    ) : null;

  const createQuoteButton = (id: number, row: Row) =>
    canAdd("sales.quotes") && canQuoteOpportunity(row) ? (
      <Button
        variant="contained"
        color="secondary"
        startIcon={<RequestQuoteOutlinedIcon />}
        disabled={busy}
        onClick={() => void createQuote(id)}
      >
        {busyKey === `quote-${id}` ? "Creating…" : "Create quote"}
      </Button>
    ) : null;

  const lostDialog = (
    <LostStageDialog
      open={lost !== null}
      loading={busy}
      onClose={() => setLost(null)}
      onConfirm={(reason) => {
        if (!lost) return;
        void moveStage(lost.id, "lost", reason, () => {
          const done = lost.onDone;
          setLost(null);
          done?.();
        });
      }}
    />
  );

  return {
    convertLead,
    createQuote,
    moveStage,
    askLost,
    completeActivity,
    leadRowActions,
    opportunityRowActions,
    activityRowActions,
    convertLeadButton,
    createQuoteButton,
    lostDialog,
  };
}
