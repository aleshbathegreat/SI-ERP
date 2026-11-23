"use client";

import { useEffect, useState } from "react";
import { Box, Button, CircularProgress, Stack, Typography } from "@mui/material";
import PrintIcon from "@mui/icons-material/Print";
import { useParams, useRouter } from "next/navigation";
import { useSnackbar } from "notistack";
import ModuleGate from "@/components/ModuleGate";
import PageHeader from "@/components/PageHeader";
import { errorSnackbarOpts, getApiErrorMessage } from "@/lib/apiError";
import {
  fetchItemLabel,
  printItemLabel,
  qrImageSrc,
  type ItemLabel,
} from "@/lib/printLabel";

export default function ItemLabelPage() {
  const params = useParams();
  const id = String(params.id);
  const router = useRouter();
  const { enqueueSnackbar } = useSnackbar();
  const [label, setLabel] = useState<ItemLabel | null>(null);

  useEffect(() => {
    fetchItemLabel(id)
      .then(setLabel)
      .catch((e: unknown) =>
        enqueueSnackbar(getApiErrorMessage(e, "Failed to load label"), errorSnackbarOpts)
      );
  }, [id, enqueueSnackbar]);

  return (
    <ModuleGate module="inventory.items">
      <PageHeader
        title="Item label"
        subtitle="Barcode / QR label for shelf or bin"
        actions={
          <Stack direction="row" spacing={1}>
            <Button onClick={() => router.push(`/inventory/items/${id}`)}>Back</Button>
            <Button
              variant="contained"
              startIcon={<PrintIcon />}
              disabled={!label}
              onClick={() =>
                printItemLabel(id).catch((e: unknown) =>
                  enqueueSnackbar(getApiErrorMessage(e, "Print failed"), errorSnackbarOpts)
                )
              }
            >
              Print label
            </Button>
          </Stack>
        }
      />
      {!label ? (
        <Stack alignItems="center" p={6}>
          <CircularProgress />
        </Stack>
      ) : (
        <Box
          sx={{
            width: 300,
            p: 2,
            border: "1px dashed",
            borderColor: "divider",
            borderRadius: 1,
            textAlign: "center",
          }}
        >
          <Typography fontWeight={700}>{label.name}</Typography>
          <Typography variant="body2">SKU: {label.sku}</Typography>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={qrImageSrc(label.barcode, 140)}
            alt={`QR ${label.barcode}`}
            width={140}
            height={140}
            style={{ display: "block", margin: "8px auto" }}
          />
          <Typography sx={{ fontFamily: "monospace", letterSpacing: 2 }}>
            {label.barcode}
          </Typography>
        </Box>
      )}
    </ModuleGate>
  );
}
