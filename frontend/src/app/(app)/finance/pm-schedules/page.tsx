"use client";

import { useState } from "react";
import { Box } from "@mui/material";
import EntityListRoute from "@/components/crud/EntityListRoute";
import { useMaintenanceActions } from "@/components/maintenance/useMaintenanceActions";
import { getEntityDef } from "@/lib/entityCrudDefs";

const def = getEntityDef("finance/pm-schedules")!;

export default function Page() {
  const { generateDueButton } = useMaintenanceActions();
  const [tick, setTick] = useState(0);
  return (
    <>
      <Box sx={{ display: "flex", justifyContent: "flex-end", mb: 1 }}>
        {generateDueButton(() => setTick((t) => t + 1))}
      </Box>
      <EntityListRoute key={tick} def={def} />
    </>
  );
}