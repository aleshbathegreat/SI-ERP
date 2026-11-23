"use client";

import EntityListRoute from "@/components/crud/EntityListRoute";
import { useQmsActions } from "@/components/qms/useQmsActions";
import { getEntityDef } from "@/lib/entityCrudDefs";

const def = getEntityDef("qms/inspections")!;

export default function Page() {
  const { inspectionRowActions } = useQmsActions();
  return (
    <EntityListRoute
      def={def}
      getRowActions={(row, { reload }) => inspectionRowActions(row)}
    />
  );
}