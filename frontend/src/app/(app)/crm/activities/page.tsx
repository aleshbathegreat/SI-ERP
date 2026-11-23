"use client";

import EntityListRoute from "@/components/crud/EntityListRoute";
import { useCrmActions } from "@/components/crm/useCrmActions";
import { getEntityDef } from "@/lib/entityCrudDefs";

const def = getEntityDef("crm/activities")!;

export default function Page() {
  const { activityRowActions } = useCrmActions();
  return (
    <EntityListRoute
      def={def}
      getRowActions={(row, ctx) => activityRowActions(row, ctx)}
    />
  );
}
