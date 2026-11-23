"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { Button } from "@mui/material";
import PrintIcon from "@mui/icons-material/Print";
import EntityFormRoute from "@/components/crud/EntityFormRoute";
import { getEntityDef } from "@/lib/entityCrudDefs";

const def = getEntityDef("inventory/items")!;

export default function Page() {
  const params = useParams();
  return (
    <EntityFormRoute
      moduleKey={def.moduleKey}
      resourcePath={def.apiPath}
      entityLabel={def.entityLabel}
      basePath={`/${def.route}`}
      mode="view"
      id={String(params.id)}
      fields={def.fields}
      empty={def.empty}
      viewTitleField="name"
      viewActions={() => (
        <Button
          startIcon={<PrintIcon />}
          component={Link}
          href={`/inventory/items/${String(params.id)}/label`}
        >
          Print label
        </Button>
      )}
      viewSections={[
        {
          title: "Identity",
          fields: ["sku", "name", "barcode", "category", "item_type", "unit", "is_active"],
        },
        {
          title: "Warehouse & valuation",
          fields: [
            "default_warehouse",
            "valuation_method",
            "unit_cost",
            "sales_price",
            "qty_on_hand",
            "reorder_level",
            "max_level",
          ],
        },
        { title: "Description", fields: ["description"] },
      ]}
    />
  );
}