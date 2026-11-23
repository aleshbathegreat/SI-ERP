"use client";

import { useRouter } from "next/navigation";
import { Button } from "@mui/material";
import AccountTreeOutlinedIcon from "@mui/icons-material/AccountTreeOutlined";
import SwapHorizIcon from "@mui/icons-material/SwapHoriz";
import BoltOutlinedIcon from "@mui/icons-material/BoltOutlined";
import NotificationsActiveOutlinedIcon from "@mui/icons-material/NotificationsActiveOutlined";
import TextFieldsOutlinedIcon from "@mui/icons-material/TextFieldsOutlined";
import PlayArrowOutlinedIcon from "@mui/icons-material/PlayArrowOutlined";
import ScheduleOutlinedIcon from "@mui/icons-material/ScheduleOutlined";
import ListAltOutlinedIcon from "@mui/icons-material/ListAltOutlined";
import EntityListRoute from "@/components/crud/EntityListRoute";
import { getEntityDef } from "@/lib/entityCrudDefs";
import api from "@/lib/api";
import { useSnackbar } from "notistack";
import { errorSnackbarOpts, getApiErrorMessage } from "@/lib/apiError";

const def = getEntityDef("dms/workflows")!;

export default function Page() {
  const router = useRouter();
  const { enqueueSnackbar } = useSnackbar();
  return (
    <EntityListRoute
      def={def}
      getRowActions={(row) => {
        const go = (part: string) => () => router.push(`/dms/workflows/${row.id}/${part}`);
        return [
          {
            key: "states",
            label: "States",
            icon: <AccountTreeOutlinedIcon fontSize="small" />,
            onClick: go("states"),
            dividerBefore: true,
          },
          {
            key: "transitions",
            label: "Transitions",
            icon: <SwapHorizIcon fontSize="small" />,
            onClick: go("transitions"),
          },
          {
            key: "events",
            label: "Events",
            icon: <NotificationsActiveOutlinedIcon fontSize="small" />,
            onClick: go("events"),
          },
          {
            key: "fields",
            label: "Fields",
            icon: <TextFieldsOutlinedIcon fontSize="small" />,
            onClick: go("fields"),
          },
          {
            key: "triggers",
            label: "Triggers",
            icon: <BoltOutlinedIcon fontSize="small" />,
            onClick: go("triggers"),
          },
          {
            key: "actions",
            label: "Actions",
            icon: <PlayArrowOutlinedIcon fontSize="small" />,
            onClick: go("actions"),
          },
          {
            key: "escalations",
            label: "Escalations",
            icon: <ScheduleOutlinedIcon fontSize="small" />,
            onClick: go("escalations"),
          },
          {
            key: "records",
            label: "Records",
            icon: <ListAltOutlinedIcon fontSize="small" />,
            onClick: go("records"),
          },
        ];
      }}
      toolbarExtra={(ctx) => (
        <Button
          variant="outlined"
          onClick={() => {
            void api
              .post("/dms/workflows/ensure-standard/")
              .then(() => {
                enqueueSnackbar("Standard document workflow is ready", { variant: "success" });
                ctx.reload();
              })
              .catch((e) => {
                enqueueSnackbar(getApiErrorMessage(e, "Could not create the workflow"), errorSnackbarOpts);
              });
          }}
        >
          Use standard workflow
        </Button>
      )}
    />
  );
}
