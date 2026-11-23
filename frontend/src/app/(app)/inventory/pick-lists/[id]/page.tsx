"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  Button,
  MenuItem,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";
import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutlined";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import { useSnackbar } from "notistack";
import DetailPageShell from "@/components/crud/DetailPageShell";
import ModuleGate from "@/components/ModuleGate";
import { usePermissions } from "@/hooks/usePermissions";
import { useRecordAction } from "@/hooks/useRecordAction";
import { getResource, listResource } from "@/lib/crudApi";
import { errorSnackbarOpts, getApiErrorMessage } from "@/lib/apiError";

type Line = {
  id: number;
  item_sku: string;
  item_name: string;
  qty: string;
  bin: number | null;
  bin_code: string;
  picked_qty: string;
};

type PickList = {
  id: number;
  pick_no: string;
  status: string;
  warehouse: number;
  warehouse_code: string;
  sales_order: number | null;
  sales_order_no: string;
  delivery_note: number | null;
  delivery_note_no: string;
  notes: string;
  lines: Line[];
};

type Bin = { id: number; code: string; warehouse: number };

const moduleKey = "inventory.pick_lists";
const apiPath = "/inventory/pick-lists/";

export default function Page() {
  const params = useParams();
  const id = String(params.id);
  const { enqueueSnackbar } = useSnackbar();
  const { canChange } = usePermissions();
  const { run, busy } = useRecordAction();
  const [pl, setPl] = useState<PickList | null>(null);
  const [bins, setBins] = useState<Bin[]>([]);
  const [loading, setLoading] = useState(true);
  const [edits, setEdits] = useState<Record<number, { picked_qty: string; bin: string }>>({});

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getResource<PickList>(apiPath, id);
      setPl(data);
      setEdits(
        Object.fromEntries(
          data.lines.map((l) => [
            l.id,
            { picked_qty: l.picked_qty && Number(l.picked_qty) > 0 ? l.picked_qty : l.qty, bin: l.bin ? String(l.bin) : "" },
          ])
        )
      );
      const b = await listResource<Bin>("/inventory/bins/", { warehouse: data.warehouse });
      setBins(b);
    } catch (e) {
      enqueueSnackbar(getApiErrorMessage(e, "Failed to load pick list"), errorSnackbarOpts);
    } finally {
      setLoading(false);
    }
  }, [id, enqueueSnackbar]);

  useEffect(() => {
    void load();
  }, [load]);

  const done = pl?.status === "done";
  const canEdit = canChange(moduleKey) && !done;

  const confirmPick = async () => {
    if (!pl) return;
    const lines = pl.lines.map((l) => ({
      id: l.id,
      picked_qty: edits[l.id]?.picked_qty ?? l.qty,
      ...(edits[l.id]?.bin ? { bin: Number(edits[l.id].bin) } : {}),
    }));
    const res = await run(`confirm-${id}`, `${apiPath}${id}/confirm/`, {
      body: { lines },
      success: pl.delivery_note
        ? "Pick confirmed"
        : "Pick confirmed — delivery note posted",
    });
    if (res) await load();
  };

  const start = async () => {
    const res = await run(`start-${id}`, `${apiPath}${id}/start/`, {
      success: "Picking started",
    });
    if (res) await load();
  };

  return (
    <ModuleGate module={moduleKey}>
      <DetailPageShell
        eyebrow="Pick list"
        title={pl?.pick_no || "Pick list"}
        backHref="/inventory/pick-lists"
        status={pl?.status}
        loading={loading}
        subtitle={
          pl
            ? [
                `Warehouse ${pl.warehouse_code}`,
                pl.sales_order_no && `SO ${pl.sales_order_no}`,
                pl.delivery_note_no && `DN ${pl.delivery_note_no}`,
              ]
                .filter(Boolean)
                .join(" · ")
            : undefined
        }
        extraActions={
          <>
            {canEdit && pl?.status === "draft" ? (
              <Button
                variant="outlined"
                startIcon={<PlayArrowIcon />}
                disabled={busy}
                onClick={() => void start()}
              >
                Start picking
              </Button>
            ) : null}
            {canEdit ? (
              <Button
                variant="contained"
                color="secondary"
                startIcon={<CheckCircleOutlineIcon />}
                disabled={busy}
                onClick={() => void confirmPick()}
              >
                {pl?.delivery_note ? "Confirm pick" : "Confirm pick & post delivery"}
              </Button>
            ) : null}
            {pl?.delivery_note ? (
              <Button
                component={Link}
                href={`/sales/deliveries/${pl.delivery_note}`}
                variant="outlined"
              >
                {pl.delivery_note_no || "Delivery note"}
              </Button>
            ) : null}
          </>
        }
      >
        {pl ? (
          <Paper variant="outlined" sx={{ p: 2 }}>
            <Typography variant="subtitle1" sx={{ mb: 1 }}>
              Lines
            </Typography>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>SKU</TableCell>
                  <TableCell>Item</TableCell>
                  <TableCell align="right">Qty</TableCell>
                  <TableCell>Bin</TableCell>
                  <TableCell align="right">Picked</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {pl.lines.map((l) => (
                  <TableRow key={l.id}>
                    <TableCell>{l.item_sku}</TableCell>
                    <TableCell>{l.item_name}</TableCell>
                    <TableCell align="right">{l.qty}</TableCell>
                    <TableCell sx={{ minWidth: 160 }}>
                      {canEdit ? (
                        <TextField
                          select
                          size="small"
                          fullWidth
                          value={edits[l.id]?.bin ?? ""}
                          onChange={(e) =>
                            setEdits((p) => ({
                              ...p,
                              [l.id]: { ...p[l.id], bin: e.target.value },
                            }))
                          }
                        >
                          <MenuItem value="">— No bin —</MenuItem>
                          {bins.map((b) => (
                            <MenuItem key={b.id} value={String(b.id)}>
                              {b.code}
                            </MenuItem>
                          ))}
                        </TextField>
                      ) : (
                        l.bin_code || "—"
                      )}
                    </TableCell>
                    <TableCell align="right" sx={{ width: 140 }}>
                      {canEdit ? (
                        <TextField
                          size="small"
                          type="number"
                          value={edits[l.id]?.picked_qty ?? ""}
                          onChange={(e) =>
                            setEdits((p) => ({
                              ...p,
                              [l.id]: { ...p[l.id], picked_qty: e.target.value },
                            }))
                          }
                        />
                      ) : (
                        l.picked_qty
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
              {pl.delivery_note
                ? "This delivery already left the warehouse. Confirming records the pick and does not move stock again."
                : "Confirming takes the picked quantity out of the bin and posts a delivery note for the same quantity."}
            </Typography>
            {pl.notes ? (
              <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                {pl.notes}
              </Typography>
            ) : null}
          </Paper>
        ) : null}
      </DetailPageShell>
    </ModuleGate>
  );
}
