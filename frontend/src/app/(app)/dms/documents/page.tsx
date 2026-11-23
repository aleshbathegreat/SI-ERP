"use client";

import EntityListRoute from "@/components/crud/EntityListRoute";
import { getEntityDef } from "@/lib/entityCrudDefs";
import { Office365ImportButton } from "./Office365Save";

const def = getEntityDef("dms/documents")!;

export default function Page() {
  return (
    <EntityListRoute
      def={def}
      toolbarExtra={(ctx) => <Office365ImportButton onDone={ctx.reload} />}
    />
  );
}
