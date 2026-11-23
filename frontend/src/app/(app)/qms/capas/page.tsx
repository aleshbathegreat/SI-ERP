"use client";

import EntityListRoute from "@/components/crud/EntityListRoute";
import { useQmsActions } from "@/components/qms/useQmsActions";
import { getEntityDef } from "@/lib/entityCrudDefs";

const def = getEntityDef("qms/capas")!;

export default function Page() {
  const { capaRowActions } = useQmsActions();
  return (
    <EntityListRoute
      def={def}
      getRowActions={(row, { reload }) => capaRowActions(row, reload)}
    />
  );
}