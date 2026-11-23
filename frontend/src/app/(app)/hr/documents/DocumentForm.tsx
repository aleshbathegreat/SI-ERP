"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Button, Link as MuiLink, Stack, TextField } from "@mui/material";
import { useSnackbar } from "notistack";
import DateTextField, { endBeforeStart, todayISO } from "@/components/DateTextField";
import EditIcon from "@mui/icons-material/Edit";
import FormPageShell from "@/components/crud/FormPageShell";
import DetailPageShell, {
  DetailGrid,
  DetailItem,
  DetailSection,
} from "@/components/crud/DetailPageShell";
import RelationSelect, { RELATIONS } from "@/components/crud/RelationSelect";
import ModuleGate from "@/components/ModuleGate";
import { useEntityForm, type FormMode } from "@/hooks/useEntityForm";
import { usePermissions } from "@/hooks/usePermissions";
import { formatDate } from "@/lib/format";
import api from "@/lib/api";
import { errorSnackbarOpts, getApiErrorMessage } from "@/lib/apiError";

const empty = {
  employee: "",
  title: "",
  doc_type: "general",
  reference: "",
  issued_on: todayISO(),
  expires_on: "",
  notes: "",
  file: "",
  file_url: "",
  file_obj: null as File | null,
};

const BASE = "/hr/documents";
const MODULE = "hr.documents";

function resolveFileHref(file?: string, fileUrl?: string): string | null {
  const raw = (fileUrl || file || "").trim();
  if (!raw) return null;
  if (/^https?:\/\//i.test(raw)) return raw;
  const api = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api";
  const origin = api.replace(/\/api\/?$/, "");
  return raw.startsWith("/") ? `${origin}${raw}` : `${origin}/${raw}`;
}

export default function DocumentForm({ mode, id }: { mode: FormMode; id?: string }) {
  const { canChange } = usePermissions();
  const router = useRouter();
  const { enqueueSnackbar } = useSnackbar();
  const [uploading, setUploading] = useState(false);
  const { form, setForm, loading, saving, readOnly } = useEntityForm({
    resourcePath: "/hr/documents/",
    entityLabel: "Document",
    basePath: BASE,
    mode,
    id,
    empty,
    mapLoaded: (row) => ({
      employee: String(row.employee ?? ""),
      title: String(row.title ?? ""),
      doc_type: String(row.doc_type ?? "general"),
      reference: String(row.reference ?? ""),
      issued_on: String(row.issued_on ?? ""),
      expires_on: String(row.expires_on ?? ""),
      notes: String(row.notes ?? ""),
      file: String(row.file ?? ""),
      file_url: String(row.file_url ?? ""),
      file_obj: null,
    }),
  });

  const fileHref = resolveFileHref(form.file, form.file_url);

  const save = async () => {
    if (mode === "view") {
      router.push(BASE);
      return;
    }
    if (endBeforeStart(form.issued_on, form.expires_on)) {
      enqueueSnackbar("Expires on cannot be before the start date.", { variant: "warning" });
      return;
    }
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append("employee", String(Number(form.employee)));
      fd.append("title", String(form.title));
      fd.append("doc_type", String(form.doc_type || "general"));
      fd.append("reference", String(form.reference || ""));
      if (form.issued_on) fd.append("issued_on", String(form.issued_on));
      if (form.expires_on) fd.append("expires_on", String(form.expires_on));
      fd.append("notes", String(form.notes || ""));
      if (form.file_obj instanceof File) {
        fd.append("file", form.file_obj);
      }
      if (mode === "edit" && id != null) {
        await api.patch(`/hr/documents/${id}/`, fd, {
          headers: { "Content-Type": "multipart/form-data" },
        });
        enqueueSnackbar("Document updated", { variant: "success" });
      } else {
        await api.post("/hr/documents/", fd, {
          headers: { "Content-Type": "multipart/form-data" },
        });
        enqueueSnackbar("Document created", { variant: "success" });
      }
      router.push(BASE);
    } catch (e: unknown) {
      enqueueSnackbar(getApiErrorMessage(e, "Could not save document"), errorSnackbarOpts);
    } finally {
      setUploading(false);
    }
  };

  if (mode === "view") {
    return (
      <ModuleGate module={MODULE}>
        <DetailPageShell
          eyebrow="Document"
          title={String(form.title || "Document")}
          subtitle={form.doc_type ? String(form.doc_type) : undefined}
          backHref={BASE}
          loading={loading}
          extraActions={
            canChange(MODULE) && id ? (
              <Button
                component={Link}
                href={`${BASE}/${id}/edit`}
                variant="contained"
                startIcon={<EditIcon />}
              >
                Edit
              </Button>
            ) : null
          }
        >
          <DetailSection title="Document" defaultExpanded>
            <DetailGrid>
              <DetailItem
                label="Employee"
                value={form.employee ? `#${form.employee}` : "—"}
              />
              <DetailItem label="Type" value={form.doc_type || "—"} />
              <DetailItem label="Reference" value={form.reference || "—"} />
              <DetailItem label="Issued" value={formatDate(String(form.issued_on))} />
              <DetailItem label="Expires" value={formatDate(String(form.expires_on))} />
              <DetailItem
                label="Attachment"
                value={
                  fileHref ? (
                    <MuiLink href={fileHref} target="_blank" rel="noopener noreferrer">
                      Open file
                    </MuiLink>
                  ) : (
                    "—"
                  )
                }
                fullWidth
              />
            </DetailGrid>
          </DetailSection>
          <DetailSection title="Notes" defaultExpanded={false}>
            <DetailItem label="Notes" value={form.notes || "—"} fullWidth />
          </DetailSection>
        </DetailPageShell>
      </ModuleGate>
    );
  }

  return (
    <ModuleGate module={MODULE}>
      <FormPageShell
        title={mode === "create" ? "New document" : "Edit document"}
        subtitle="Employee document vault"
        backHref={BASE}
        mode={mode}
        loading={loading}
        saving={saving || uploading}
        onSubmit={save}
      >
        <Stack spacing={2}>
          <DetailSection title="Identity" defaultExpanded>
            <Stack spacing={2}>
              <RelationSelect
                label="Employee"
                required
                value={form.employee}
                disabled={readOnly}
                relation={RELATIONS.employee}
                onChange={(v) => setForm({ ...form, employee: v })}
              />
              <TextField
                label="Title"
                required
                fullWidth
                value={form.title}
                disabled={readOnly}
                onChange={(e) => setForm({ ...form, title: e.target.value })}
              />
              <TextField
                label="Document type"
                fullWidth
                value={form.doc_type}
                disabled={readOnly}
                helperText="e.g. cnic, passport, contract, degree"
                onChange={(e) => setForm({ ...form, doc_type: e.target.value })}
              />
              <TextField
                label="Reference"
                fullWidth
                value={form.reference}
                disabled={readOnly}
                onChange={(e) => setForm({ ...form, reference: e.target.value })}
              />
              <Button variant="outlined" component="label" disabled={readOnly}>
                {form.file_obj instanceof File
                  ? form.file_obj.name
                  : fileHref
                    ? "Replace attachment"
                    : "Upload attachment"}
                <input
                  type="file"
                  hidden
                  onChange={(e) =>
                    setForm({
                      ...form,
                      file_obj: e.target.files?.[0] || null,
                    })
                  }
                />
              </Button>
            </Stack>
          </DetailSection>
          <DetailSection title="Dates & notes" defaultExpanded={false}>
            <Stack spacing={2}>
              <DateTextField
                label="Issued on"
                value={form.issued_on}
                disabled={readOnly}
                onChange={(e) => setForm({ ...form, issued_on: e.target.value })}
              />
              <DateTextField
                label="Expires on"
                value={form.expires_on}
                disabled={readOnly}
                notBefore={String(form.issued_on || "")}
                helperText="Used for expiry alerts (30-day window)"
                onChange={(e) => setForm({ ...form, expires_on: e.target.value })}
              />
              <TextField
                label="Notes"
                multiline
                minRows={2}
                fullWidth
                value={form.notes}
                disabled={readOnly}
                onChange={(e) => setForm({ ...form, notes: e.target.value })}
              />
            </Stack>
          </DetailSection>
        </Stack>
      </FormPageShell>
    </ModuleGate>
  );
}
