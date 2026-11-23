"use client";

import { useParams } from "next/navigation";
import EntityFormRoute from "@/components/crud/EntityFormRoute";
import { getEntityDef } from "@/lib/entityCrudDefs";

const def = getEntityDef("dms/documents")!;

export default function Page() {
  const params = useParams();
  return (
    <EntityFormRoute
      moduleKey={def.moduleKey}
      resourcePath={def.apiPath}
      entityLabel={def.entityLabel}
      basePath={`/${def.route}`}
      mode="edit"
      id={String(params.id)}
      fields={def.fields}
      empty={def.empty}
      titles={{ edit: "Edit document" }}
      mapPayload={(f) => ({
        title: f.title,
        folder: f.folder === "" || f.folder === 0 ? null : f.folder,
        category: f.category ?? "",
        related_module: f.related_module ?? "",
        related_id: f.related_id === "" || f.related_id === undefined ? null : f.related_id,
        tags: f.tags ?? "",
        notes: f.notes ?? "",
      })}
    />
  );
}
