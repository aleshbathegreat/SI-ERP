"use client";

import { Button, Stack } from "@mui/material";
import api from "@/lib/api";
import { errorSnackbarOpts, getApiErrorMessage } from "@/lib/apiError";
import { useSnackbar } from "notistack";
import { usePermissions } from "@/hooks/usePermissions";

const ACTION_LABELS: Record<string, string> = {
  submit: "Submit",
  approve: "Approve",
  reject: "Reject",
  post: "Post to GL",
};

export default function WorkflowActions({
  resourcePath,
  id,
  status,
  moduleKey,
  onDone,
  allowPost = false,
  submitLabel,
  approveLabel,
  showCancel = false,
  cancelStatuses,
}: {
  resourcePath: string;
  id: number;
  status?: string;
  moduleKey: string;
  onDone?: (updated?: { id?: number; status?: string }) => void;
  allowPost?: boolean;
  submitLabel?: string;
  approveLabel?: string;
  showCancel?: boolean;
  cancelStatuses?: string[];
}) {
  const { canAdd, canChange } = usePermissions();
  const { enqueueSnackbar } = useSnackbar();
  const base = resourcePath.endsWith("/") ? resourcePath : `${resourcePath}/`;

  const run = async (action: string) => {
    const label =
      action === "submit"
        ? submitLabel || ACTION_LABELS.submit
        : action === "approve"
          ? approveLabel || ACTION_LABELS.approve
          : ACTION_LABELS[action] || action;
    try {
      const { data } = await api.post<{ id?: number; status?: string }>(
        `${base}${id}/${action}/`
      );
      enqueueSnackbar(`${label} successful`, { variant: "success" });
      onDone?.(data);
    } catch (e: unknown) {
      enqueueSnackbar(
        getApiErrorMessage(e, `${label} failed`),
        errorSnackbarOpts
      );
    }
  };

  const st = (status || "").toLowerCase();
  const canSubmit =
    canAdd(moduleKey) && ["draft", "open", "pending"].includes(st);
  const canApprove =
    canChange(moduleKey) &&
    ["submitted", "pending", "processing", "interview"].includes(st);
  const canPost = allowPost && canChange(moduleKey) && st === "approved";
  const canCancel =
    showCancel &&
    canChange(moduleKey) &&
    (cancelStatuses || ["draft", "submitted", "approved", "confirmed"]).includes(st);

  if (!canSubmit && !canApprove && !canPost && !canCancel) return null;

  return (
    <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
      {canSubmit ? (
        <Button
          size="small"
          variant="outlined"
          onClick={(e) => {
            e.stopPropagation();
            void run("submit");
          }}
        >
          {submitLabel || "Submit"}
        </Button>
      ) : null}
      {canApprove ? (
        <>
          <Button
            size="small"
            variant="contained"
            onClick={(e) => {
              e.stopPropagation();
              void run("approve");
            }}
          >
            {approveLabel || "Approve"}
          </Button>
          <Button
            size="small"
            color="error"
            variant="outlined"
            onClick={(e) => {
              e.stopPropagation();
              void run("reject");
            }}
          >
            Reject
          </Button>
        </>
      ) : null}
      {canPost ? (
        <Button
          size="small"
          color="secondary"
          variant="contained"
          onClick={(e) => {
            e.stopPropagation();
            void run("post");
          }}
        >
          Post to GL
        </Button>
      ) : null}
      {canCancel ? (
        <Button
          size="small"
          color="error"
          variant="text"
          onClick={(e) => {
            e.stopPropagation();
            void run("cancel");
          }}
        >
          Cancel
        </Button>
      ) : null}
    </Stack>
  );
}
