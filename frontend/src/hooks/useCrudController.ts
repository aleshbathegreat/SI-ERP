"use client";

import { useCallback, useEffect, useState } from "react";
import { useSnackbar } from "notistack";
import {
  bulkDeleteResource,
  createResource,
  deleteResource,
  listResource,
  updateResource,
} from "@/lib/crudApi";
import { errorSnackbarOpts, getApiErrorMessage } from "@/lib/apiError";

type Mode = "create" | "edit" | "view" | null;

export function useCrudController<T extends { id: number }>(resourcePath: string, entityLabel: string) {
  const { enqueueSnackbar } = useSnackbar();
  const [rows, setRows] = useState<T[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [mode, setMode] = useState<Mode>(null);
  const [active, setActive] = useState<T | null>(null);
  const [confirm, setConfirm] = useState<{
    type: "one" | "bulk";
    row?: T;
  } | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await listResource<T>(resourcePath);
      setRows(data);
      setSelectedIds([]);
    } catch (e: unknown) {
      enqueueSnackbar(
        getApiErrorMessage(e, `Failed to load ${entityLabel}`),
        errorSnackbarOpts
      );
    } finally {
      setLoading(false);
    }
  }, [resourcePath, entityLabel, enqueueSnackbar]);

  useEffect(() => {
    load();
  }, [load]);

  const openCreate = () => {
    setActive(null);
    setMode("create");
  };

  const openEdit = (row: T) => {
    setActive(row);
    setMode("edit");
  };

  const openView = (row: T) => {
    setActive(row);
    setMode("view");
  };

  const closeForm = () => {
    setMode(null);
    setActive(null);
  };

  const save = async (payload: Partial<T>) => {
    setSaving(true);
    try {
      if (mode === "edit" && active) {
        await updateResource<T>(resourcePath, active.id, payload);
        enqueueSnackbar(`${entityLabel} updated`, { variant: "success" });
      } else {
        await createResource<T>(resourcePath, payload);
        enqueueSnackbar(`${entityLabel} created`, { variant: "success" });
      }
      closeForm();
      await load();
    } catch (e: unknown) {
      enqueueSnackbar(
        getApiErrorMessage(e, `Could not save ${entityLabel}`),
        errorSnackbarOpts
      );
    } finally {
      setSaving(false);
    }
  };

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
    mode,
    active,
    confirm,
    setConfirm,
    load,
    openCreate,
    openEdit,
    openView,
    closeForm,
    save,
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
