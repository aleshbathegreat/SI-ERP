"use client";

import PostAddIcon from "@mui/icons-material/PostAdd";
import { useSnackbar } from "notistack";
import EntityListRoute from "@/components/crud/EntityListRoute";
import { usePermissions } from "@/hooks/usePermissions";
import api from "@/lib/api";
import { errorSnackbarOpts, getApiErrorMessage } from "@/lib/apiError";
import { getEntityDef } from "@/lib/entityCrudDefs";

const def = getEntityDef("finance/intercompany-txns")!;

export default function Page() {
  const { canAdd } = usePermissions();
  const { enqueueSnackbar } = useSnackbar();

  return (
    <EntityListRoute
      def={def}
      getRowActions={(row, { reload }) =>
        row.status === "draft" && canAdd(def.moduleKey)
          ? [
              {
                key: "post",
                label: "Post to GL",
                icon: <PostAddIcon fontSize="small" />,
                onClick: async () => {
                  try {
                    await api.post(`${def.apiPath}${row.id}/post/`);
                    enqueueSnackbar("Posted to GL", { variant: "success" });
                    reload();
                  } catch (e: unknown) {
                    enqueueSnackbar(
                      getApiErrorMessage(e, "Post failed"),
                      errorSnackbarOpts
                    );
                  }
                },
              },
            ]
          : []
      }
    />
  );
}
