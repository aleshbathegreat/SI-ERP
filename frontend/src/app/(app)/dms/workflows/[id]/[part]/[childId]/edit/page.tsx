"use client";

import { notFound, useParams } from "next/navigation";
import { WorkflowPart, isWorkflowPart } from "../../../../WorkflowPart";

export default function Page() {
  const params = useParams();
  const part = String(params.part);
  if (!isWorkflowPart(part) || part === "records") notFound();
  return (
    <WorkflowPart
      workflowId={String(params.id)}
      part={part}
      mode="edit"
      childId={String(params.childId)}
    />
  );
}
