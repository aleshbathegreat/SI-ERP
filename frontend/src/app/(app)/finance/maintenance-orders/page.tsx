"use client";

import EntityListRoute from "@/components/crud/EntityListRoute";
import { useMaintenanceActions } from "@/components/maintenance/useMaintenanceActions";
import { getEntityDef } from "@/lib/entityCrudDefs";

const def = getEntityDef("finance/maintenance-orders")!;

export default function Page() {
  const { rowActions } = useMaintenanceActions();
  return (
    <EntityListRoute
      def={def}
      getRowActions={(row, { reload }) => rowActions(row, reload)}
    />
  );
}