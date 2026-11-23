"use client";

import EntityListRoute from "@/components/crud/EntityListRoute";
import { useTimesheetActions } from "@/components/projects/useTimesheetActions";
import { getEntityDef } from "@/lib/entityCrudDefs";

const def = getEntityDef("projects/timesheets")!;

export default function Page() {
  const { rowActions } = useTimesheetActions();
  return (
    <EntityListRoute
      def={def}
      getRowActions={(row, { reload }) => rowActions(row, reload)}
    />
  );
}
