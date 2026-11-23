"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useSnackbar } from "notistack";
import {
  bulkDeleteResource,
  deleteResource,
  listResource,
} from "@/lib/crudApi";
import { errorSnackbarOpts, getApiErrorMessage } from "@/lib/apiError";

/** List + delete only; create/view/edit navigate to dedicated routes. */
export function useCrudList<T extends { id: number }>(
  resourcePath: string,
  entityLabel: string,
  basePath: string,
  opts?: { createHref?: string }
) {
  const router = useRouter();
  const { enqueueSnackbar } = useSnackbar();
  const [rows, setRows] = useState<T[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [confirm, setConfirm] = useState<{
    type: "one" | "bulk";
    row?: T;
  } | null>(null);
  const loadSeq = useRef(0);

  const load = useCallback(async (opts?: { silent?: boolean }) => {
    const silent = !!opts && opts.silent === true;
    const seq = ++loadSeq.current;
    if (!silent) setLoading(true);
    try {
      const data = await listResource<T>(resourcePath);
      if (seq !== loadSeq.current) return;
      setRows(data);
      if (!silent) setSelectedIds([]);
    } catch (e: unknown) {
      if (seq !== loadSeq.current) return;
      enqueueSnackbar(
        getApiErrorMessage(e, `Failed to load ${entityLabel}`),
        errorSnackbarOpts
      );
    } finally {
      if (seq === loadSeq.current) setLoading(false);
    }
  }, [resourcePath, entityLabel, enqueueSnackbar]);

  const patchRow = useCallback((id: number, partial: Partial<T>) => {
    setRows((prev) => prev.map((row) => (row.id === id ? { ...row, ...partial } : row)));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const openCreate = () =>
    router.push(opts?.createHref || `${basePath}/new`);
  const openEdit = (row: T) => router.push(`${basePath}/${row.id}/edit`);
  const openView = (row: T) => router.push(`${basePath}/${row.id}`);

  const askDeleteOne = (row: T) => setConfirm({ type: "one", row });
  const askBulkDelete = () => {
    if (!selectedIds.length) return;
    setConfirm({ type: "bulk" });
  };

  const runConfirmDelete = async () => {
    if (!confirm) return;
    setSaving(true);
    try {
      if (confirm.type === "one" && confirm.row) {
        await deleteResource(resourcePath, confirm.row.id);
        enqueueSnackbar(`${entityLabel} deleted`, { variant: "success" });
      } else {
        const deleted = await bulkDeleteResource(resourcePath, selectedIds);
        enqueueSnackbar(`${deleted} ${entityLabel}(s) deleted`, { variant: "success" });
      }
      setConfirm(null);
      await load();
    } catch (e: unknown) {
      enqueueSnackbar(
        getApiErrorMessage(e, `Could not delete ${entityLabel}`),
        errorSnackbarOpts
      );
    } finally {
      setSaving(false);
    }
  };

  return {
    rows,
    loading,
    saving,
    selectedIds,
    setSelectedIds,
    confirm,
    setConfirm,
    load,
    patchRow,
    openCreate,
    openEdit,
    openView,
    askDeleteOne,
    askBulkDelete,
    runConfirmDelete,
    toggleAll: (checked: boolean) =>
      setSelectedIds(checked ? rows.map((r) => r.id) : []),
    toggleOne: (id: number, checked: boolean) =>
      setSelectedIds((prev) =>
        checked ? [...new Set([...prev, id])] : prev.filter((x) => x !== id)
      ),
  };
}
