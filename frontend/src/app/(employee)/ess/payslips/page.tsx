"use client";

import { useEffect, useState } from "react";
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  Dialog,
  DialogContent,
  DialogTitle,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";
import PrintOutlinedIcon from "@mui/icons-material/PrintOutlined";
import EssSection, { EssPanel } from "@/components/ess/EssSection";
import { EssPayslip, fetchEssPayslips, fetchEssTaxCertificate, openEssPayslipPrint } from "@/lib/essApi";
import { errorSnackbarOpts, getApiErrorMessage } from "@/lib/apiError";
import { useSnackbar } from "notistack";

export default function EssPayslipsPage() {
  const { enqueueSnackbar } = useSnackbar();
  const [rows, setRows] = useState<EssPayslip[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");
  const [printing, setPrinting] = useState<number | null>(null);
  const [certificate, setCertificate] = useState<Record<string, string> | null>(null);

  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        setRows(await fetchEssPayslips());
      } catch (e: unknown) {
        setErr(getApiErrorMessage(e, "Could not load payslips"));
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const print = async (id: number) => {
    setPrinting(id);
    try {
      await openEssPayslipPrint(id);
    } catch (e: unknown) {
      enqueueSnackbar(getApiErrorMessage(e, "Could not open payslip"), errorSnackbarOpts);
    } finally {
      setPrinting(null);
    }
  };

  if (loading) {
    return (
      <Box sx={{ display: "grid", placeItems: "center", minHeight: 240 }}>
        <CircularProgress size={32} />
      </Box>
    );
  }

  return (
    <EssSection
      title="Payslips"
      subtitle="View net pay and print or save as PDF."
    >
      {err ? (
        <Alert severity="error" sx={{ mb: 2 }}>
          {err}
        </Alert>
      ) : null}

      <Button
        variant="outlined"
        sx={{ mb: 2 }}
        onClick={async () => {
          try {
            setCertificate(await fetchEssTaxCertificate());
          } catch (e: unknown) {
            enqueueSnackbar(getApiErrorMessage(e, "Could not open the tax certificate"), errorSnackbarOpts);
          }
        }}
      >
        Tax certificate
      </Button>
      <EssPanel>
        {rows.length === 0 ? (
          <Typography color="text.secondary">No payslips available yet.</Typography>
        ) : (
          <Box sx={{ overflowX: "auto" }}>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Cycle</TableCell>
                  <TableCell align="right">Basic</TableCell>
                  <TableCell align="right">Allowances</TableCell>
                  <TableCell align="right">Gross</TableCell>
                  <TableCell align="right">Deductions</TableCell>
                  <TableCell align="right">Net</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell />
                </TableRow>
              </TableHead>
              <TableBody>
                {rows.map((p) => (
                  <TableRow key={p.id} hover>
                    <TableCell>{p.period_name || `Period #${p.period}`}</TableCell>
                    <TableCell align="right">{Number(p.basic || 0).toLocaleString()}</TableCell>
                    <TableCell align="right">{Number(p.allowances || 0).toLocaleString()}</TableCell>
                    <TableCell align="right">{Number(p.gross_pay || 0).toLocaleString()}</TableCell>
                    <TableCell align="right">{Number(p.total_deductions || 0).toLocaleString()}</TableCell>
                    <TableCell align="right">
                      {Number(p.net_pay).toLocaleString()} {p.currency || "PKR"}
                    </TableCell>
                    <TableCell>{p.status || "—"}</TableCell>
                    <TableCell>
                      <Button
                        size="small"
                        variant="outlined"
                        startIcon={<PrintOutlinedIcon />}
                        disabled={printing === p.id}
                        onClick={() => print(p.id)}
                      >
                        PDF
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Box>
        )}
      </EssPanel>
      <Dialog open={!!certificate} onClose={() => setCertificate(null)} fullWidth maxWidth="sm">
        <DialogTitle>Tax certificate {certificate?.fiscal_year}</DialogTitle>
        <DialogContent>
          <Typography fontWeight={700}>{certificate?.employee_name}</Typography>
          <Typography variant="body2" color="text.secondary">
            {certificate?.organization} · {certificate?.period_from} to {certificate?.period_to}
          </Typography>
          <Typography sx={{ mt: 1 }}>Gross {certificate?.total_gross}</Typography>
          <Typography>Tax withheld {certificate?.total_tax}</Typography>
          <Typography>Net {certificate?.total_net}</Typography>
        </DialogContent>
      </Dialog>
    </EssSection>
  );
}
