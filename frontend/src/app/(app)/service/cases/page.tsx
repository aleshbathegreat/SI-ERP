"use client";

import EntityListRoute from "@/components/crud/EntityListRoute";
import { useServiceActions } from "@/components/service/useServiceActions";
import { getEntityDef } from "@/lib/entityCrudDefs";

const def = getEntityDef("service/cases")!;

export default function Page() {
  const { rowActions } = useServiceActions();
  return (
    <EntityListRoute
      def={def}
      getRowActions={(row, { reload }) => rowActions(row, reload)}
    />
  );
}