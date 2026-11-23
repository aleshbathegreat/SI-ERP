"use client";

import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircle";
import BlockIcon from "@mui/icons-material/Block";
import { useSnackbar } from "notistack";
import EntityListRoute from "@/components/crud/EntityListRoute";
import type { RowActionItem } from "@/components/crud/RowActionsMenu";
import { usePermissions } from "@/hooks/usePermissions";
import api from "@/lib/api";
import { errorSnackbarOpts, getApiErrorMessage } from "@/lib/apiError";
import { getEntityDef } from "@/lib/entityCrudDefs";

const def = getEntityDef("finance/cheques")!;

export default function Page() {
  const { canAdd } = usePermissions();
  const { enqueueSnackbar } = useSnackbar();

  const run = async (
    id: number,
    action: "clear" | "bounce",
    reload: () => void,
    body: Record<string, unknown> = {}
  ) => {
    try {
      await api.post(`${def.apiPath}${id}/${action}/`, body);
      enqueueSnackbar(action === "clear" ? "Cheque cleared" : "Cheque bounced", {
        variant: "success",
      });
      reload();
    } catch (e: unknown) {
      enqueueSnackbar(getApiErrorMessage(e, `Could not ${action} cheque`), errorSnackbarOpts);
    }
  };

  return (
    <EntityListRoute
      def={def}
      getRowActions={(row, { reload }) => {
        const status = String(row.status || "");
        if (!canAdd(def.moduleKey)) return [];
        const items: RowActionItem[] = [];
        if (status === "issued") {
          items.push({
            key: "clear",
            label: "Mark cleared (post GL)",
            icon: <CheckCircleOutlineIcon fontSize="small" />,
            onClick: () => run(row.id, "clear", reload),
          });
        }
        if (status === "issued" || status === "cleared") {
          items.push({
            key: "bounce",
            label: "Mark bounced",
            icon: <BlockIcon fontSize="small" />,
            danger: true,
            onClick: () => {
              const reason = window.prompt("Bounce reason (optional)") ?? "";
              run(row.id, "bounce", reload, { reason });
            },
          });
        }
        return items;
      }}
    />
  );
}
