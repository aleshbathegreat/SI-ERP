"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Chip,
  MenuItem,
  Stack,
  TextField,
} from "@mui/material";
import { useSnackbar } from "notistack";
import CrudTable from "@/components/crud/CrudTable";
import ConfirmDialog from "@/components/crud/ConfirmDialog";
import ModuleGate from "@/components/ModuleGate";
import { usePermissions } from "@/hooks/usePermissions";
import {
  bulkDeleteResource,
  deleteResource,
  listResource,
} from "@/lib/crudApi";
import { errorSnackbarOpts, getApiErrorMessage } from "@/lib/apiError";

type Asset = {
  id: number;
  asset_code: string;
  name: string;
  category: string;
  location: string;
  custodian: string;
  assigned_employee: number | null;
  assigned_employee_name?: string;
  status: string;
  book_value: string | number;
  open_repair_count?: number;
};

type Emp = {
  id: number;
  employee_code: string;
  first_name: string;
  last_name: string;
};

const MODULE = "finance.assets";
const API = "/finance/assets/";
const BASE = "/finance/assets";
const STATUSES = ["", "active", "in_repair", "idle", "disposed"];

export default function Page() {
  const router = useRouter();
  const { enqueueSnackbar } = useSnackbar();
  const { canAdd, canChange, canDelete } = usePermissions();
  const [rows, setRows] = useState<Asset[]>([]);
  const [employees, setEmployees] = useState<Emp[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [confirm, setConfirm] = useState<{
    type: "one" | "bulk";
    row?: Asset;
  } | null>(null);
  const [status, setStatus] = useState("");
  const [category, setCategory] = useState("");
  const [assignee, setAssignee] = useState("");
  const [search, setSearch] = useState("");
  const [searchDraft, setSearchDraft] = useState("");

  const categories = useMemo(() => {
    const set = new Set<string>();
    rows.forEach((r) => {
      if (r.category) set.add(r.category);
    });
    return Array.from(set).sort();
  }, [rows]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await listResource<Asset>(API, {
        status: status || undefined,
        category: category || undefined,
        assigned_employee: assignee || undefined,
        search: search || undefined,
      });
      setRows(data);
      setSelectedIds([]);
    } catch (e: unknown) {
      enqueueSnackbar(
        getApiErrorMessage(e, "Failed to load fixed assets"),
        errorSnackbarOpts
      );
    } finally {
      setLoading(false);
    }
  }, [status, category, assignee, search, enqueueSnackbar]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    listResource<Emp>("/hr/employees/")
      .then(setEmployees)
      .catch(() => undefined);
  }, []);

  const runConfirmDelete = async () => {
    if (!confirm) return;
    setSaving(true);
    try {
      if (confirm.type === "one" && confirm.row) {
        await deleteResource(API, confirm.row.id);
        enqueueSnackbar("Fixed asset deleted", { variant: "success" });
      } else {
        const deleted = await bulkDeleteResource(API, selectedIds);
        enqueueSnackbar(`${deleted} fixed asset(s) deleted`, {
          variant: "success",
        });
      }
      setConfirm(null);
      await load();
    } catch (e: unknown) {
      enqueueSnackbar(
        getApiErrorMessage(e, "Could not delete fixed asset"),
        errorSnackbarOpts
      );
    } finally {
      setSaving(false);
    }
  };

  return (
    <ModuleGate module={MODULE}>
      <>
        <CrudTable
          title="Fixed assets"
          subtitle="Register, assignment, repairs, and QR stickers"
          rows={rows}
          loading={loading}
          selectedIds={selectedIds}
          onToggleAll={(checked) =>
            setSelectedIds(checked ? rows.map((r) => r.id) : [])
          }
          onToggleOne={(id, checked) =>
            setSelectedIds((prev) =>
              checked
                ? [...new Set([...prev, id])]
                : prev.filter((x) => x !== id)
            )
          }
          onRefresh={load}
          onCreate={() => router.push(`${BASE}/new`)}
          onEdit={(row) => router.push(`${BASE}/${row.id}/edit`)}
          onView={(row) => router.push(`${BASE}/${row.id}`)}
          onDeleteOne={(row) => setConfirm({ type: "one", row })}
          onBulkDelete={() => {
            if (selectedIds.length) setConfirm({ type: "bulk" });
          }}
          createLabel="Add asset"
          canCreate={canAdd(MODULE)}
          canEdit={canChange(MODULE)}
          canDelete={canDelete(MODULE)}
          emptyTitle="No fixed assets yet"
          emptyHint="Add an asset to start the register, assignment, and repairs."
          toolbarExtra={
            <>
              <TextField
                size="small"
                label="Search"
                value={searchDraft}
                onChange={(e) => setSearchDraft(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") setSearch(searchDraft.trim());
                }}
                onBlur={() => setSearch(searchDraft.trim())}
              />
              <TextField
                select
                size="small"
                label="Status"
                value={status}
                onChange={(e) => setStatus(e.target.value)}
              >
                {STATUSES.map((s) => (
                  <MenuItem key={s || "all"} value={s}>
                    {s || "All statuses"}
                  </MenuItem>
                ))}
              </TextField>
              <TextField
                select
                size="small"
                label="Category"
                value={category}
                onChange={(e) => setCategory(e.target.value)}
              >
                <MenuItem value="">All categories</MenuItem>
                {categories.map((c) => (
                  <MenuItem key={c} value={c}>
                    {c}
                  </MenuItem>
                ))}
                {category && !categories.includes(category) ? (
                  <MenuItem value={category}>{category}</MenuItem>
                ) : null}
              </TextField>
              <TextField
                select
                size="small"
                label="Assignee"
                value={assignee}
                onChange={(e) => setAssignee(e.target.value)}
              >
                <MenuItem value="">All assignees</MenuItem>
                {employees.map((e) => (
                  <MenuItem key={e.id} value={String(e.id)}>
                    {e.employee_code} — {e.first_name} {e.last_name}
                  </MenuItem>
                ))}
              </TextField>
            </>
          }
          columns={[
            { key: "code", header: "Code", render: (r) => r.asset_code },
            { key: "name", header: "Name", render: (r) => r.name },
            {
              key: "category",
              header: "Category",
              render: (r) => r.category || "—",
            },
            {
              key: "assignee",
              header: "Assignee",
              render: (r) => r.assigned_employee_name || r.custodian || "—",
            },
            {
              key: "location",
              header: "Location",
              render: (r) => r.location || "—",
            },
            {
              key: "book",
              header: "Book value",
              render: (r) => String(r.book_value ?? "—"),
            },
            {
              key: "repairs",
              header: "Open repairs",
              render: (r) =>
                r.open_repair_count ? String(r.open_repair_count) : "0",
            },
            {
              key: "status",
              header: "Status",
              render: (r) => (
                <Chip size="small" label={r.status} variant="outlined" />
              ),
            },
          ]}
        />
        <ConfirmDialog
          open={!!confirm}
          title={
            confirm?.type === "bulk"
              ? "Delete selected fixed assets?"
              : "Delete fixed asset?"
          }
          message={
            confirm?.type === "bulk"
              ? `Soft-delete ${selectedIds.length} asset(s)?`
              : `Delete “${confirm?.row?.asset_code ?? ""} — ${confirm?.row?.name ?? ""}”?`
          }
          confirmLabel="Delete"
          loading={saving}
          onClose={() => setConfirm(null)}
          onConfirm={runConfirmDelete}
        />
      </>
    </ModuleGate>
  );
}
