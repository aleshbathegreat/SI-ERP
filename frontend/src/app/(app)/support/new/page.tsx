"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { MenuItem, Stack, TextField } from "@mui/material";
import { useSnackbar } from "notistack";
import FormPageShell from "@/components/crud/FormPageShell";
import api from "@/lib/api";

const basePath = "/support";

export default function NewTicketPage() {
  const router = useRouter();
  const { enqueueSnackbar } = useSnackbar();
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState({
    subject: "",
    body: "",
    category: "general",
    priority: "normal",
  });

  const create = async () => {
    setBusy(true);
    try {
      await api.post("/support/tickets/", form);
      enqueueSnackbar("Ticket opened", { variant: "success" });
      router.push(basePath);
    } catch {
      enqueueSnackbar("Could not create ticket", { variant: "error" });
    } finally {
      setBusy(false);
    }
  };

  return (
    <FormPageShell
      title="New support ticket"
      backHref={basePath}
      mode="create"
      saving={busy}
      onSubmit={create}
    >
      <TextField
        label="Subject"
        required
        value={form.subject}
        onChange={(e) => setForm({ ...form, subject: e.target.value })}
      />
      <Stack direction="row" spacing={1}>
        <TextField
          select
          label="Category"
          value={form.category}
          fullWidth
          onChange={(e) => setForm({ ...form, category: e.target.value })}
        >
          {["billing", "technical", "sales", "general"].map((c) => (
            <MenuItem key={c} value={c}>
              {c}
            </MenuItem>
          ))}
        </TextField>
        <TextField
          select
          label="Priority"
          value={form.priority}
          fullWidth
          onChange={(e) => setForm({ ...form, priority: e.target.value })}
        >
          {["low", "normal", "high", "urgent"].map((p) => (
            <MenuItem key={p} value={p}>
              {p}
            </MenuItem>
          ))}
        </TextField>
      </Stack>
      <TextField
        label="Message"
        required
        multiline
        minRows={4}
        value={form.body}
        onChange={(e) => setForm({ ...form, body: e.target.value })}
      />
    </FormPageShell>
  );
}
