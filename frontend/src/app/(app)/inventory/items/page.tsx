"use client";

import PrintIcon from "@mui/icons-material/Print";
import { useSnackbar } from "notistack";
import EntityListRoute from "@/components/crud/EntityListRoute";
import { errorSnackbarOpts, getApiErrorMessage } from "@/lib/apiError";
import { getEntityDef } from "@/lib/entityCrudDefs";
import { printItemLabel } from "@/lib/printLabel";

const def = getEntityDef("inventory/items")!;

export default function Page() {
  const { enqueueSnackbar } = useSnackbar();
  return (
    <EntityListRoute
      def={def}
      getRowActions={(row) => [
        {
          key: "label",
          label: "Print label",
          icon: <PrintIcon fontSize="small" />,
          onClick: () =>
            printItemLabel(row.id).catch((e: unknown) =>
              enqueueSnackbar(getApiErrorMessage(e, "Print failed"), errorSnackbarOpts)
            ),
        },
      ]}
    />
  );
}
