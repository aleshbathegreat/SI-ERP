"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Box,
  Chip,
  Paper,
  Stack,
  Typography,
} from "@mui/material";
import { useSnackbar } from "notistack";
import api from "@/lib/api";
import { errorSnackbarOpts, getApiErrorMessage } from "@/lib/apiError";
import { formatMoney } from "@/lib/format";
import { usePermissions } from "@/hooks/usePermissions";
import RowActionsMenu from "@/components/crud/RowActionsMenu";
import { useCrmActions } from "@/components/crm/useCrmActions";

type NextActivity = {
  subject: string;
  due_date: string | null;
  is_overdue: boolean;
};

type Card = {
  id: number;
  name: string;
  customer_name?: string;
  lead_name?: string;
  amount: string;
  probability: number;
  priority: string;
  stage: string;
  expected_close: string | null;
  owner_name?: string;
  next_activity: NextActivity | null;
};

type Column = {
  stage: string;
  label: string;
  probability: number;
  count: number;
  amount: string;
  truncated: boolean;
  cards: Card[];
};

const BORDER: Record<string, string> = {
  prospecting: "info.main",
  proposal: "primary.main",
  negotiation: "warning.main",
  won: "success.main",
  lost: "text.disabled",
};

function dayLabel(value?: string | null) {
  if (!value) return "";
  const [year, month, day] = value.slice(0, 10).split("-").map(Number);
  if (!year || !month || !day) return value;
  return new Date(year, month - 1, day).toLocaleDateString("en-GB", {
    day: "2-digit",
    month: "short",
  });
}

export default function PipelineBoard({ onChanged }: { onChanged?: () => void }) {
  const router = useRouter();
  const { enqueueSnackbar } = useSnackbar();
  const { canChange, canAdd } = usePermissions();
  const crm = useCrmActions();
  const [columns, setColumns] = useState<Column[]>([]);
  const [loading, setLoading] = useState(true);
  const [over, setOver] = useState<string | null>(null);
  const dragged = useRef(false);
  const canMove = canChange("crm.opportunities");

  const load = useCallback(() => {
    setLoading(true);
    api
      .get<Column[]>("/crm/opportunities/board/")
      .then((res) => setColumns(res.data))
      .catch((error) => {
        setColumns([]);
        enqueueSnackbar(getApiErrorMessage(error, "Could not load the pipeline"), errorSnackbarOpts);
      })
      .finally(() => setLoading(false));
  }, [enqueueSnackbar]);

  useEffect(() => {
    load();
  }, [load]);

  const moveTo = (id: number, stage: string, closeReason?: string) => {
    void crm.moveStage(id, stage, closeReason, () => {
      load();
      onChanged?.();
    });
  };

  const onDrop = (stage: string, event: React.DragEvent) => {
    event.preventDefault();
    setOver(null);
    if (!canMove) return;
    const raw = event.dataTransfer.getData("text/plain");
    const id = Number(raw);
    if (!id) return;
    const card = columns.flatMap((column) => column.cards).find((row) => row.id === id);
    if (!card || card.stage === stage) return;
    if (stage === "lost") {
      crm.askLost(id, () => {
        load();
        onChanged?.();
      });
      return;
    }
    moveTo(id, stage);
  };

  return (
    <>
      {crm.lostDialog}
      {loading && columns.length === 0 ? (
        <Typography variant="body2" color="text.secondary">
          Loading pipeline…
        </Typography>
      ) : (
        <Box sx={{ overflowX: "auto", pb: 1 }}>
          <Stack direction="row" spacing={1.5} alignItems="flex-start" sx={{ minWidth: 1080 }}>
            {columns.map((column) => (
              <Paper
                key={column.stage}
                variant="outlined"
                onDragOver={(event) => {
                  if (!canMove) return;
                  event.preventDefault();
                  setOver(column.stage);
                }}
                onDragLeave={() => setOver((current) => (current === column.stage ? null : current))}
                onDrop={(event) => onDrop(column.stage, event)}
                sx={{
                  width: 260,
                  flex: "0 0 260px",
                  p: 1,
                  bgcolor: over === column.stage ? "action.hover" : "background.paper",
                  borderTop: 3,
                  borderTopColor: BORDER[column.stage] || "divider",
                }}
              >
                <Stack direction="row" justifyContent="space-between" alignItems="baseline">
                  <Typography variant="subtitle2">{column.label}</Typography>
                  <Typography variant="caption" color="text.secondary">
                    {column.count}
                  </Typography>
                </Stack>
                <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 1 }}>
                  {formatMoney(column.amount)} · {column.probability}%
                  {column.truncated ? " · showing first 80" : ""}
                </Typography>
                <Stack spacing={1}>
                  {column.cards.map((card) => (
                    <Paper
                      key={card.id}
                      variant="outlined"
                      draggable={canMove}
                      onDragStart={(event) => {
                        dragged.current = true;
                        event.dataTransfer.setData("text/plain", String(card.id));
                        event.dataTransfer.effectAllowed = "move";
                      }}
                      onClick={() => {
                        if (dragged.current) {
                          dragged.current = false;
                          return;
                        }
                        router.push(`/crm/opportunities/${card.id}`);
                      }}
                      sx={{
                        p: 1,
                        cursor: "pointer",
                        "&:hover": { bgcolor: "action.hover" },
                      }}
                    >
                      <Stack direction="row" justifyContent="space-between" alignItems="flex-start">
                        <Typography variant="body2" sx={{ fontWeight: 600, pr: 0.5 }}>
                          {card.name}
                        </Typography>
                        <Box onClick={(event) => event.stopPropagation()}>
                          <RowActionsMenu
                            onView={() => router.push(`/crm/opportunities/${card.id}`)}
                            onEdit={
                              canMove
                                ? () => router.push(`/crm/opportunities/${card.id}/edit`)
                                : undefined
                            }
                            extraActions={[
                              ...(canAdd("sales.quotes") && card.stage !== "lost"
                                ? [
                                    {
                                      key: "quote",
                                      label: "Create quote",
                                      onClick: () => crm.createQuote(card.id),
                                    },
                                  ]
                                : []),
                              ...(canMove
                                ? columns
                                    .filter((item) => item.stage !== card.stage)
                                    .map((item) => ({
                                      key: `move-${item.stage}`,
                                      label: `Move to ${item.label}`,
                                      dividerBefore: item.stage === "won",
                                      danger: item.stage === "lost",
                                      onClick: () => {
                                        if (item.stage === "lost") {
                                          crm.askLost(card.id, () => {
                                            load();
                                            onChanged?.();
                                          });
                                          return;
                                        }
                                        moveTo(card.id, item.stage);
                                      },
                                    }))
                                : []),
                            ]}
                          />
                        </Box>
                      </Stack>
                      <Typography variant="caption" color="text.secondary" display="block">
                        {card.customer_name || card.lead_name || "No customer"}
                        {card.owner_name ? ` · ${card.owner_name}` : ""}
                      </Typography>
                      <Stack direction="row" spacing={0.5} useFlexGap flexWrap="wrap" sx={{ mt: 0.75 }}>
                        <Chip size="small" label={formatMoney(card.amount)} />
                        {card.priority && card.priority !== "normal" ? (
                          <Chip
                            size="small"
                            label={card.priority}
                            color={card.priority === "urgent" ? "error" : "warning"}
                            variant="outlined"
                          />
                        ) : null}
                      </Stack>
                      <Typography
                        variant="caption"
                        color={card.next_activity?.is_overdue ? "error" : "text.secondary"}
                        display="block"
                        sx={{ mt: 0.75 }}
                      >
                        {card.expected_close ? `Close ${dayLabel(card.expected_close)}` : "No close date"}
                        {card.next_activity
                          ? ` · ${card.next_activity.is_overdue ? "Overdue: " : ""}${card.next_activity.subject}`
                          : ""}
                      </Typography>
                    </Paper>
                  ))}
                  {column.cards.length === 0 ? (
                    <Typography variant="caption" color="text.secondary" sx={{ px: 0.5, py: 1 }}>
                      Drop a deal here
                    </Typography>
                  ) : null}
                </Stack>
              </Paper>
            ))}
          </Stack>
        </Box>
      )}
    </>
  );
}
