"use client";

import { Chip } from "@mui/material";
import { ReactNode } from "react";
import CrudTable from "@/components/crud/CrudTable";
import ConfirmDialog from "@/components/crud/ConfirmDialog";
import type { RowActionItem } from "@/components/crud/RowActionsMenu";
import ModuleGate from "@/components/ModuleGate";
import { useCrudList } from "@/hooks/useCrudList";
import { usePermissions } from "@/hooks/usePermissions";
import type { EntityCrudDef } from "@/lib/entityCrudDefs";

type Row = { id: number } & Record<string, unknown>;

export default function EntityListRoute({
  def,
  getRowActions,
  renderRowAction,
  toolbarExtra,
}: {
  def: EntityCrudDef;
  /** Extra per-row menu actions (e.g. workflow / convert). */
  getRowActions?: (
    row: Row,
    ctx: { reload: () => void }
  ) => RowActionItem[];
  renderRowAction?: (row: Row) => ReactNode;
  toolbarExtra?: ReactNode | ((ctx: { reload: () => void }) => ReactNode);
}) {
  const basePath = `/${def.route}`;
  const { canAdd, canChange, canDelete } = usePermissions();
  const crud = useCrudList<Row>(def.apiPath, def.entityLabel, basePath, {
    createHref: def.createHref,
  });

  const labelField =
    def.columns.find((c) => c.key === "name" || c.key === "title")?.key ||
    def.columns[0]?.key ||
    "id";

  return (
    <ModuleGate module={def.moduleKey}>
      <>
        <CrudTable
          title={def.listTitle}
          subtitle={def.listSubtitle}
          rows={crud.rows}
          loading={crud.loading}
          selectedIds={crud.selectedIds}
          onToggleAll={crud.toggleAll}
          onToggleOne={crud.toggleOne}
          onRefresh={crud.load}
          onCreate={crud.openCreate}
          onEdit={crud.openEdit}
          onView={crud.openView}
          onDeleteOne={crud.askDeleteOne}
          onBulkDelete={crud.askBulkDelete}
          createLabel={def.createLabel || `Add ${def.entityLabel.toLowerCase()}`}
          canCreate={
            !def.readOnly &&
            (def.createHref
              ? canChange(def.createModuleKey || def.moduleKey) ||
                canAdd(def.moduleKey)
              : canAdd(def.moduleKey))
          }
          canEdit={!def.readOnly && canChange(def.moduleKey)}
          canDelete={!def.readOnly && canDelete(def.moduleKey)}
          emptyTitle={def.emptyTitle}
          emptyHint={def.emptyHint}
          toolbarExtra={
            typeof toolbarExtra === "function"
              ? toolbarExtra({ reload: crud.load })
              : toolbarExtra
          }
          getRowActions={
            getRowActions
              ? (row) => getRowActions(row, { reload: crud.load })
              : undefined
          }
          renderRowAction={renderRowAction}
          columns={def.columns.map((c) => ({
            key: c.key,
            header: c.header,
            render: (r: Row) => {
              const v = r[c.key];
              if (c.chip) {
                return (
                  <Chip size="small" label={String(v ?? "—")} variant="outlined" />
                );
              }
              if (typeof v === "boolean") return v ? "Yes" : "No";
              return v == null || v === "" ? "—" : String(v);
            },
          }))}
        />
        <ConfirmDialog
          open={!!crud.confirm}
          title={
            crud.confirm?.type === "bulk"
              ? `Delete selected ${def.listTitle.toLowerCase()}?`
              : `Delete ${def.entityLabel.toLowerCase()}?`
          }
          message={
            crud.confirm?.type === "bulk"
              ? `Permanently delete ${crud.selectedIds.length} ${def.entityLabel.toLowerCase()}(s)?`
              : `Delete “${String(crud.confirm?.row?.[labelField] ?? "")}”?`
          }
          confirmLabel="Delete"
          loading={crud.saving}
          onClose={() => crud.setConfirm(null)}
          onConfirm={crud.runConfirmDelete}
        />
      </>
    </ModuleGate>
  );
}
