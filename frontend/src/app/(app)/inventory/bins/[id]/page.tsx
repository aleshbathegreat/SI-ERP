"use client";

import { useParams } from "next/navigation";
import EntityFormRoute from "@/components/crud/EntityFormRoute";
import { getEntityDef } from "@/lib/entityCrudDefs";
import BinStockPanel from "../BinStockPanel";

const def = getEntityDef("inventory/bins")!;

export default function Page() {
  const params = useParams();
  const id = String(params.id);
  return (
    <EntityFormRoute
      moduleKey={def.moduleKey}
      resourcePath={def.apiPath}
      entityLabel={def.entityLabel}
      basePath={`/${def.route}`}
      mode="view"
      id={id}
      fields={def.fields}
      empty={def.empty}
      viewTitleField="code"
      viewExtra={({ form, reload }) => (
        <BinStockPanel
          binId={id}
          stock={(form.stock as BinStockRow[]) || []}
          onChanged={reload}
        />
      )}
    />
  );
}

type BinStockRow = { item: number; item_sku: string; item_name: string; qty: string };
