"use client";

import { useEffect, useState } from "react";
import { Stack, ToggleButton, ToggleButtonGroup } from "@mui/material";
import EntityListRoute from "@/components/crud/EntityListRoute";
import PipelineBoard from "@/components/crm/PipelineBoard";
import PipelineSummary from "@/components/crm/PipelineSummary";
import { useCrmActions } from "@/components/crm/useCrmActions";
import { getEntityDef } from "@/lib/entityCrudDefs";

const def = getEntityDef("crm/opportunities")!;

export default function Page() {
  const { opportunityRowActions, lostDialog } = useCrmActions();
  const [view, setView] = useState<"board" | "list">("board");
  const [tick, setTick] = useState(0);

  useEffect(() => {
    const saved = window.sessionStorage.getItem("crm-opp-view");
    if (saved === "list" || saved === "board") setView(saved);
  }, []);

  return (
    <>
      {lostDialog}
      <Stack direction="row" justifyContent="flex-end" sx={{ mb: 1 }}>
        <ToggleButtonGroup
          size="small"
          exclusive
          value={view}
          onChange={(_, next: "board" | "list" | null) => {
            if (!next) return;
            setView(next);
            window.sessionStorage.setItem("crm-opp-view", next);
          }}
        >
          <ToggleButton value="board">Board</ToggleButton>
          <ToggleButton value="list">List</ToggleButton>
        </ToggleButtonGroup>
      </Stack>
      <PipelineSummary refreshKey={tick} />
      {view === "board" ? (
        <PipelineBoard onChanged={() => setTick((value) => value + 1)} />
      ) : (
        <EntityListRoute
          def={def}
          getRowActions={(row, ctx) => opportunityRowActions(row, ctx)}
        />
      )}
    </>
  );
}
