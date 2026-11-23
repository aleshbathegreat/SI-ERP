"use client";

import EntityFormRoute from "@/components/crud/EntityFormRoute";
import { getEntityDef } from "@/lib/entityCrudDefs";

const def = getEntityDef("finance/asset-depreciation")!;

export default function Page() {
  return <EntityFormRoute def={def} mode="edit" />;
}
