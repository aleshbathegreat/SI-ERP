"use client";

import EntityListRoute from "@/components/crud/EntityListRoute";
import { useQmsActions } from "@/components/qms/useQmsActions";
import { getEntityDef } from "@/lib/entityCrudDefs";

const def = getEntityDef("qms/ncrs")!;

export default function Page() {
  const { ncrRowActions } = useQmsActions();
  return (
    <EntityListRoute
      def={def}
      getRowActions={(row, { reload }) => ncrRowActions(row, reload)}
    />
  );
}