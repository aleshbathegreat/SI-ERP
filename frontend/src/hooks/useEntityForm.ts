"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useSnackbar } from "notistack";
import {
  createResource,
  getResource,
  updateResource,
} from "@/lib/crudApi";
import { errorSnackbarOpts, getApiErrorMessage } from "@/lib/apiError";
import { dateOrderIssue } from "@/components/DateTextField";

export type FormMode = "create" | "edit" | "view";

type RequiredField = {
  name: string;
  label: string;
  required?: boolean;
  autoGenerate?: boolean;
  type?: string;
};

function domFilled(name: string, current: unknown): unknown {
  if (current != null && String(current).trim() !== "") return current;
  if (typeof document === "undefined") return current;
  const safe = name.replace(/[^A-Za-z0-9_-]/g, "");
  if (!safe) return current;
  const nodes = document.querySelectorAll<HTMLInputElement | HTMLTextAreaElement>(
    `input[name="${safe}"], textarea[name="${safe}"]`
  );
  for (const el of nodes) {
    const value = el.value.trim();
    if (value) return value;
  }
  return current;
}

export function useEntityForm<T extends Record<string, unknown>>(opts: {
  resourcePath: string;
  entityLabel: string;
  basePath: string;
  mode: FormMode;
  id?: string | number;
  empty: T;
  mapLoaded?: (row: Record<string, unknown>) => T;
  mapPayload?: (form: T) => unknown;
  fields?: RequiredField[];
}) {
  const {
    resourcePath,
    entityLabel,
    basePath,
    mode,
    id,
    empty,
    mapLoaded,
    mapPayload,
    fields,
  } = opts;
  const router = useRouter();
  const { enqueueSnackbar } = useSnackbar();
  const [form, setForm] = useState<T>(empty);
  const [loading, setLoading] = useState(mode !== "create");
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    if (mode === "create" || id == null) {
      setForm(empty);
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const row = (await getResource<Record<string, unknown>>(
        resourcePath,
        id
      )) as Record<string, unknown>;
      setForm(mapLoaded ? mapLoaded(row) : ({ ...empty, ...row } as T));
    } catch (e: unknown) {
      enqueueSnackbar(
        getApiErrorMessage(e, `Failed to load ${entityLabel}`),
        errorSnackbarOpts
      );
      router.replace(basePath);
    } finally {
      setLoading(false);
    }
  }, [
    mode,
    id,
    empty,
    resourcePath,
    mapLoaded,
    enqueueSnackbar,
    entityLabel,
    router,
    basePath,
  ]);

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode, id, resourcePath]);

  const save = async () => {
    if (mode === "view") {
      router.push(basePath);
      return;
    }
    const merged = { ...form };
    for (const key of Object.keys(merged)) {
      merged[key] = domFilled(key, merged[key]);
    }
    if (mode !== "view" && fields?.length) {
      const missing = fields.filter((f) => {
        if (!f.required || f.type === "boolean") return false;
        if (f.autoGenerate && mode === "create") return false;
        const value = merged[f.name];
        return value == null || (typeof value === "string" && value.trim() === "");
      });
      if (missing.length) {
        enqueueSnackbar(missing.map((f) => `${f.label} is required`).join(" · "), {
          variant: "warning",
        });
        return;
      }
    }
    const order = dateOrderIssue(merged);
    if (order) {
      enqueueSnackbar(order.message, { variant: "warning" });
      return;
    }
    setSaving(true);
    try {
      const payload = mapPayload ? mapPayload(merged) : merged;
      if (mode === "edit" && id != null) {
        await updateResource(resourcePath, id, payload);
        enqueueSnackbar(`${entityLabel} updated`, { variant: "success" });
      } else {
        await createResource(resourcePath, payload);
        enqueueSnackbar(`${entityLabel} created`, { variant: "success" });
      }
      router.push(basePath);
    } catch (e: unknown) {
      enqueueSnackbar(
        getApiErrorMessage(e, `Could not save ${entityLabel}`),
        errorSnackbarOpts
      );
    } finally {
      setSaving(false);
    }
  };

  return {
    form,
    setForm,
    loading,
    saving,
    save,
    reload: load,
    readOnly: mode === "view",
  };
}
