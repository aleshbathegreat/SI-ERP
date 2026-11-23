"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";
import { useParams, useRouter } from "next/navigation";
import { useSnackbar } from "notistack";
import ModuleGate from "@/components/ModuleGate";
import PageHeader from "@/components/PageHeader";
import { usePermissions } from "@/hooks/usePermissions";
import api from "@/lib/api";
import { errorSnackbarOpts, getApiErrorMessage } from "@/lib/apiError";
import { formatDate, formatMoney } from "@/lib/format";

type Line = {
  id: number;
  line_type: string;
  description: string;
  tax_code: string;
  taxable_amount: string;
  tax_amount: string;
  source_type: string;
  source_ref: string;
};

type TaxReturn = {
  id: number;
  return_type: string;
  period_start: string;
  period_end: string;
  status: string;
  notes: string;
  filing_ref: string;
  filed_at?: string | null;
  totals?: Record<string, string | number | string[] | undefined>;
  lines: Line[];
};

const moduleKey = "finance.tax_returns";
const apiPath = "/finance/tax-returns/";

export default function TaxReturnDetailPage() {
  const params = useParams();
  const id = String(params.id);
  const router = useRouter();
  const { canChange } = usePermissions();
  const { enqueueSnackbar } = useSnackbar();
  const [tr, setTr] = useState<TaxReturn | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [filingRef, setFilingRef] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get<TaxReturn>(`${apiPath}${id}/`);
      setTr(data);
    } catch (e: unknown) {
      enqueueSnackbar(getApiErrorMessage(e, "Failed to load return"), errorSnackbarOpts);
    } finally {
      setLoading(false);
    }
  }, [id, enqueueSnackbar]);

  useEffect(() => {
    load();
  }, [load]);

  const act = async (action: "regenerate" | "file", body: Record<string, unknown> = {}) => {
    setBusy(true);
    try {
      const { data } = await api.post<TaxReturn>(`${apiPath}${id}/${action}/`, body);
      setTr(data);
      enqueueSnackbar(action === "file" ? "Marked as filed" : "Return regenerated", {
        variant: "success",
      });
    } catch (e: unknown) {
      enqueueSnackbar(getApiErrorMessage(e, `${action} failed`), errorSnackbarOpts);
    } finally {
      setBusy(false);
    }
  };

  const exportCsv = async () => {
    try {
      const res = await api.get(`${apiPath}${id}/export-csv/`, { responseType: "blob" });
      const url = URL.createObjectURL(res.data as Blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `tax-return-${tr?.return_type}-${tr?.period_end}.csv`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e: unknown) {
      enqueueSnackbar(getApiErrorMessage(e, "Export failed"), errorSnackbarOpts);
    }
  };

  const draft = tr?.status === "draft";
  const totals = tr?.totals || {};

  return (
    <ModuleGate module={moduleKey}>
      <PageHeader
        title={
          tr
            ? `${tr.return_type === "wht" ? "WHT" : "Sales tax"} return`
            : "Tax return"
        }
        subtitle={
          tr ? `${formatDate(tr.period_start)} → ${formatDate(tr.period_end)}` : undefined
        }
        actions={
          <Stack direction="row" spacing={1}>
            <Button onClick={() => router.push("/finance/tax-returns")}>Back</Button>
            <Button onClick={exportCsv} disabled={!tr}>
              Export CSV
            </Button>
            {draft && canChange(moduleKey) ? (
              <Button disabled={busy} onClick={() => act("regenerate")}>
                Regenerate
              </Button>
            ) : null}
          </Stack>
        }
      />
      {loading || !tr ? (
        <Stack alignItems="center" p={6}>
          <CircularProgress />
        </Stack>
      ) : (
        <Stack spacing={2}>
          <Box
            sx={{
              display: "grid",
              gap: 2,
              gridTemplateColumns: { xs: "1fr", md: "repeat(4, 1fr)" },
            }}
          >
            {(
              [
                ["Taxable value", totals.taxable_total],
                ["Tax charged", totals.tax_total],
                ["Deposited (challans)", totals.deposited],
                ["Net payable", totals.net_payable],
              ] as const
            ).map(([label, value]) => (
              <Card key={label} variant="outlined">
                <CardContent>
                  <Typography variant="body2" color="text.secondary">
                    {label}
                  </Typography>
                  <Typography variant="h5">{formatMoney(Number(value ?? 0))}</Typography>
                </CardContent>
              </Card>
            ))}
          </Box>
          <Stack direction="row" spacing={1} alignItems="center">
            <Chip
              size="small"
              label={tr.status}
              color={tr.status === "filed" ? "success" : "default"}
              variant="outlined"
            />
            {tr.filed_at ? (
              <Typography variant="body2" color="text.secondary">
                Filed {formatDate(tr.filed_at)} {tr.filing_ref ? `· ${tr.filing_ref}` : ""}
              </Typography>
            ) : null}
          </Stack>
          {Array.isArray(totals.notes) && totals.notes.length ? (
            <Typography variant="body2" color="text.secondary">
              {totals.notes.join(" ")}
            </Typography>
          ) : null}
          <Card variant="outlined">
            <CardContent>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Type</TableCell>
                    <TableCell>Description</TableCell>
                    <TableCell>Code</TableCell>
                    <TableCell align="right">Taxable</TableCell>
                    <TableCell align="right">Tax</TableCell>
                    <TableCell>Source</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {tr.lines.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={6}>
                        No documents in this period (approved/paid invoices and challans).
                      </TableCell>
                    </TableRow>
                  ) : (
                    tr.lines.map((l) => (
                      <TableRow key={l.id}>
                        <TableCell>{l.line_type}</TableCell>
                        <TableCell>{l.description}</TableCell>
                        <TableCell>{l.tax_code || "—"}</TableCell>
                        <TableCell align="right">
                          {formatMoney(Number(l.taxable_amount))}
                        </TableCell>
                        <TableCell align="right">{formatMoney(Number(l.tax_amount))}</TableCell>
                        <TableCell>
                          {l.source_type ? `${l.source_type}: ${l.source_ref}` : "—"}
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
          {draft && canChange(moduleKey) ? (
            <Stack direction="row" spacing={1} alignItems="center">
              <TextField
                size="small"
                label="Filing reference (IRIS)"
                value={filingRef}
                onChange={(e) => setFilingRef(e.target.value)}
              />
              <Button
                variant="contained"
                disabled={busy}
                onClick={() => act("file", { filing_ref: filingRef })}
              >
                Mark as filed
              </Button>
            </Stack>
          ) : null}
        </Stack>
      )}
    </ModuleGate>
  );
}
