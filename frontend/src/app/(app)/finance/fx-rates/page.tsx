"use client";

import EntityListRoute from "@/components/crud/EntityListRoute";
import { getEntityDef } from "@/lib/entityCrudDefs";

const def = getEntityDef("finance/fx-rates")!;

export default function Page() {
  return <EntityListRoute def={def} />;
}
