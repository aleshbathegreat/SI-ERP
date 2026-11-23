"use client";

import CrudTable from "@/components/crud/CrudTable";
import ConfirmDialog from "@/components/crud/ConfirmDialog";
import ModuleGate from "@/components/ModuleGate";
import { useCrudList } from "@/hooks/useCrudList";
import { usePermissions } from "@/hooks/usePermissions";
import { formatDate } from "@/lib/format";

type Doc = {
  id: number;
  employee: number;
  employee_name?: string;
  title: string;
  doc_type: string;
  reference?: string;
  issued_on?: string | null;
  expires_on?: string | null;
};

const MODULE = "hr.documents";

export default function DocumentsPage() {
  const { canAdd, canChange, canDelete } = usePermissions();
  const crud = useCrudList<Doc>("/hr/documents/", "Document", "/hr/documents");

  return (
    <ModuleGate module={MODULE}>
      <CrudTable
        title="Documents"
        subtitle="Employee document vault"
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
        createLabel="Add document"
        canCreate={canAdd(MODULE)}
        canEdit={canChange(MODULE)}
        canDelete={canDelete(MODULE)}
        emptyTitle="No documents yet"
        emptyHint="Add an employee document to start the vault."
        columns={[
          { key: "title", header: "Title", render: (r) => r.title },
          { key: "type", header: "Type", render: (r) => r.doc_type || "—" },
          {
            key: "emp",
            header: "Employee",
            render: (r) => r.employee_name || r.employee,
          },
          {
            key: "issued",
            header: "Issued",
            render: (r) => formatDate(r.issued_on),
          },
          {
            key: "expires",
            header: "Expires",
            render: (r) => formatDate(r.expires_on),
          },
        ]}
      />
      <ConfirmDialog
        open={!!crud.confirm}
        title={
          crud.confirm?.type === "bulk" ? "Delete selected documents?" : "Delete document?"
        }
        message={
          crud.confirm?.type === "bulk"
            ? `Permanently delete ${crud.selectedIds.length} document(s)?`
            : `Delete “${crud.confirm?.row?.title || "document"}”?`
        }
        confirmLabel="Delete"
        loading={crud.saving}
        onClose={() => crud.setConfirm(null)}
        onConfirm={crud.runConfirmDelete}
      />
    </ModuleGate>
  );
}
