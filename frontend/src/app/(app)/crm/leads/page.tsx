"use client";

import EntityListRoute from "@/components/crud/EntityListRoute";
import { useCrmActions } from "@/components/crm/useCrmActions";
import { getEntityDef } from "@/lib/entityCrudDefs";

const def = getEntityDef("crm/leads")!;

export default function Page() {
  const { leadRowActions } = useCrmActions();
  return <EntityListRoute def={def} getRowActions={(row) => leadRowActions(row)} />;
}
