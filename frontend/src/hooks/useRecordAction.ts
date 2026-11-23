"use client";

import { useCallback, useState } from "react";
import { useSnackbar } from "notistack";
import api from "@/lib/api";
import { errorSnackbarOpts, getApiErrorMessage } from "@/lib/apiError";

/** POST a custom DRF @action (e.g. /crm/leads/1/convert/) with snackbar feedback. */
export function useRecordAction() {
  const { enqueueSnackbar } = useSnackbar();
  const [busyKey, setBusyKey] = useState<string | null>(null);

  const run = useCallback(
    async <T = Record<string, unknown>>(
      key: string,
      url: string,
      opts?: {
        body?: unknown;
        success?: string | ((data: T) => string);
        onDone?: (data: T) => void;
      }
    ): Promise<T | null> => {
      setBusyKey(key);
      try {
        const { data } = await api.post<T>(url, opts?.body ?? {});
        const msg =
          typeof opts?.success === "function" ? opts.success(data) : opts?.success;
        if (msg) enqueueSnackbar(msg, { variant: "success" });
        opts?.onDone?.(data);
        return data;
      } catch (e: unknown) {
        enqueueSnackbar(getApiErrorMessage(e, "Action failed"), errorSnackbarOpts);
        return null;
      } finally {
        setBusyKey(null);
      }
    },
    [enqueueSnackbar]
  );

  return { run, busyKey, busy: busyKey !== null };
}
