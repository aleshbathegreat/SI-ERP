"use client";

import { FormEvent, useEffect, useState } from "react";
import {
  Button,
  Link as MuiLink,
  MenuItem,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";
import { useSnackbar } from "notistack";
import api from "@/lib/api";
import { errorSnackbarOpts, getApiErrorMessage } from "@/lib/apiError";
import { usePermissions } from "@/hooks/usePermissions";
import { formatDate } from "@/lib/format";

type Version = {
  id: number;
  version: number;
  file: string | null;
  original_filename?: string;
  file_size?: number;
  mime_type?: string;
  created_at: string;
};

type Named = { id: number; name: string; label?: string };
type Comment = { id: number; body: string; created_at: string; created_by_name?: string };
type MetaRow = { id: number; metadata_type_label?: string; metadata_type_name?: string; value: string };
type LinkRow = { id: number; target: number; target_title: string; label: string };
type WebRow = { id: number; label: string; url: string };
type AccessRow = { id: number; username: string; can_change: boolean };
type Dup = { id: number; title: string; version: number };
type UserRow = { id: number; username?: string; email?: string };

function bytes(n: number) {
  if (!n) return "0 B";
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

export function DocumentWorkspace({
  id,
  form,
  onDone,
}: {
  id: string;
  form: Record<string, unknown>;
  onDone: () => void;
}) {
  const { enqueueSnackbar } = useSnackbar();
  const { canChange } = usePermissions();
  const canEdit = canChange("dms.documents");
  const [tags, setTags] = useState<Named[]>([]);
  const [metaTypes, setMetaTypes] = useState<Named[]>([]);
  const [docs, setDocs] = useState<Named[]>([]);
  const [users, setUsers] = useState<UserRow[]>([]);
  const [duplicates, setDuplicates] = useState<Dup[]>([]);
  const [pickedTags, setPickedTags] = useState<number[]>([]);
  const [comment, setComment] = useState("");
  const [metaType, setMetaType] = useState("");
  const [metaValue, setMetaValue] = useState("");
  const [linkTarget, setLinkTarget] = useState("");
  const [linkLabel, setLinkLabel] = useState("");
  const [webLabel, setWebLabel] = useState("");
  const [webUrl, setWebUrl] = useState("");
  const [accessUser, setAccessUser] = useState("");

  const versions = (form.versions as Version[]) || [];
  const comments = (form.comments as Comment[]) || [];
  const metadata = (form.metadata_values as MetaRow[]) || [];
  const links = (form.links as LinkRow[]) || [];
  const webLinks = (form.web_links as WebRow[]) || [];
  const access = (form.access_entries as AccessRow[]) || [];
  const file = (form.file as string) || "";

  useEffect(() => {
    const ids = form.tag_items;
    setPickedTags(Array.isArray(ids) ? ids.map((n) => Number(n)) : []);
  }, [form.tag_items]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [tagRes, metaRes, docRes, dupRes] = await Promise.all([
          api.get("/dms/tags/", { params: { page_size: 200 } }),
          api.get("/dms/metadata-types/", { params: { page_size: 200 } }),
          api.get("/dms/documents/", { params: { page_size: 200 } }),
          api.get(`/dms/documents/${id}/duplicates/`),
        ]);
        if (cancelled) return;
        const rows = (data: { results?: Named[] } | Named[]) =>
          Array.isArray(data) ? data : data.results || [];
        setTags(rows(tagRes.data));
        setMetaTypes(rows(metaRes.data));
        setDocs(
          rows(docRes.data)
            .filter((d) => String(d.id) !== id)
            .map((d) => ({
              id: d.id,
              name: (d as Named & { title?: string }).title || d.name || String(d.id),
            }))
        );
        setDuplicates(Array.isArray(dupRes.data) ? dupRes.data : []);
      } catch {
        /* lists stay empty */
      }
      try {
        const userRes = await api.get("/settings/users/", { params: { page_size: 200 } });
        if (!cancelled) {
          const data = userRes.data as { results?: UserRow[] } | UserRow[];
          setUsers(Array.isArray(data) ? data : data.results || []);
        }
      } catch {
        /* user directory is optional */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [id, form.updated_at]);

  const post = async (path: string, body: unknown, ok: string) => {
    try {
      await api.post(path, body);
      enqueueSnackbar(ok, { variant: "success" });
      onDone();
    } catch (e) {
      enqueueSnackbar(getApiErrorMessage(e, "Save failed"), errorSnackbarOpts);
    }
  };

  const saveTags = (e: FormEvent) => {
    e.preventDefault();
    void post(`/dms/documents/${id}/tags/`, { tag_ids: pickedTags }, "Tags saved");
  };

  return (
    <Stack spacing={2} sx={{ mt: 2 }}>
      <Paper variant="outlined" sx={{ p: 2 }}>
        <Typography variant="subtitle1" sx={{ mb: 1 }}>
          File &amp; versions
        </Typography>
        <Typography variant="body2" sx={{ mb: 1 }}>
          {file ? (
            <MuiLink href={file} target="_blank" rel="noopener noreferrer">
              {String(form.original_filename || "Download")}
            </MuiLink>
          ) : (
            "No file uploaded"
          )}
          {form.mime_type ? ` · ${String(form.mime_type)}` : ""}
          {form.file_size ? ` · ${bytes(Number(form.file_size))}` : ""}
          {form.checksum ? ` · ${String(form.checksum).slice(0, 12)}` : ""}
          {form.external_web_url ? (
            <>
              {" · "}
              <MuiLink href={String(form.external_web_url)} target="_blank" rel="noopener noreferrer">
                Open in Microsoft 365
              </MuiLink>
            </>
          ) : null}
        </Typography>
        {duplicates.length ? (
          <Typography variant="body2" color="warning.main" sx={{ mb: 1 }}>
            Possible duplicate:{" "}
            {duplicates.map((d) => (
              <MuiLink key={d.id} href={`/dms/documents/${d.id}`} sx={{ mr: 1 }}>
                {d.title} v{d.version}
              </MuiLink>
            ))}
          </Typography>
        ) : null}
        {form.checked_out_by_name ? (
          <Typography variant="body2" sx={{ mb: 1 }}>
            Checked out by {String(form.checked_out_by_name)}
            {form.checked_out_at ? ` · ${formatDate(String(form.checked_out_at))}` : ""}
          </Typography>
        ) : null}
        {versions.length ? (
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Version</TableCell>
                <TableCell>File</TableCell>
                <TableCell>Size</TableCell>
                <TableCell>Uploaded</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {versions.map((v) => (
                <TableRow key={v.id}>
                  <TableCell>v{v.version}</TableCell>
                  <TableCell>
                    {v.file ? (
                      <MuiLink href={v.file} target="_blank" rel="noopener noreferrer">
                        {v.original_filename || "Download"}
                      </MuiLink>
                    ) : (
                      "—"
                    )}
                  </TableCell>
                  <TableCell>{bytes(v.file_size || 0)}</TableCell>
                  <TableCell>{formatDate(v.created_at)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        ) : null}
      </Paper>

      <Paper variant="outlined" sx={{ p: 2 }}>
        <Typography variant="subtitle1">Tags</Typography>
        <Typography variant="body2" sx={{ mb: 1 }}>
          {String(form.tag_names || "No tags")}
        </Typography>
        {canEdit ? (
          <Stack component="form" direction="row" spacing={1} onSubmit={saveTags}>
            <TextField
              select
              size="small"
              label="Tags"
              value={pickedTags}
              onChange={(e) => {
                const value = e.target.value;
                setPickedTags(
                  (typeof value === "string" ? value.split(",") : value).map((n) => Number(n))
                );
              }}
              slotProps={{ select: { multiple: true } }}
              sx={{ minWidth: 280 }}
            >
              {tags.map((t) => (
                <MenuItem key={t.id} value={t.id}>
                  {t.name}
                </MenuItem>
              ))}
            </TextField>
            <Button type="submit" variant="outlined">
              Save tags
            </Button>
          </Stack>
        ) : null}
      </Paper>

      <Paper variant="outlined" sx={{ p: 2 }}>
        <Typography variant="subtitle1" sx={{ mb: 1 }}>
          Metadata
        </Typography>
        {metadata.map((row) => (
          <Typography key={row.id} variant="body2">
            {row.metadata_type_label || row.metadata_type_name}: {row.value || "—"}
          </Typography>
        ))}
        {canEdit ? (
          <Stack
            component="form"
            direction="row"
            spacing={1}
            sx={{ mt: 1 }}
            onSubmit={(e) => {
              e.preventDefault();
              void post(
                `/dms/documents/${id}/metadata/`,
                { metadata_type: metaType, value: metaValue },
                "Metadata saved"
              );
            }}
          >
            <TextField
              select
              size="small"
              label="Field"
              value={metaType}
              onChange={(e) => setMetaType(e.target.value)}
              sx={{ minWidth: 180 }}
            >
              {metaTypes.map((t) => (
                <MenuItem key={t.id} value={t.id}>
                  {t.label || t.name}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              size="small"
              label="Value"
              value={metaValue}
              onChange={(e) => setMetaValue(e.target.value)}
            />
            <Button type="submit" variant="outlined" disabled={!metaType}>
              Save
            </Button>
          </Stack>
        ) : null}
      </Paper>

      <Paper variant="outlined" sx={{ p: 2 }}>
        <Typography variant="subtitle1" sx={{ mb: 1 }}>
          Comments
        </Typography>
        {comments.map((row) => (
          <Typography key={row.id} variant="body2" sx={{ mb: 0.5 }}>
            {row.created_by_name || "User"} · {formatDate(row.created_at)} — {row.body}
          </Typography>
        ))}
        {canEdit ? (
          <Stack
            component="form"
            direction="row"
            spacing={1}
            sx={{ mt: 1 }}
            onSubmit={(e) => {
              e.preventDefault();
              void post(`/dms/documents/${id}/comment/`, { body: comment }, "Comment added").then(
                () => setComment("")
              );
            }}
          >
            <TextField
              size="small"
              label="Comment"
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              fullWidth
            />
            <Button type="submit" variant="outlined" disabled={!comment.trim()}>
              Add
            </Button>
          </Stack>
        ) : null}
      </Paper>

      <Paper variant="outlined" sx={{ p: 2 }}>
        <Typography variant="subtitle1" sx={{ mb: 1 }}>
          Related documents
        </Typography>
        {links.map((row) => (
          <Typography key={row.id} variant="body2">
            <MuiLink href={`/dms/documents/${row.target}`}>{row.target_title}</MuiLink>
            {row.label ? ` · ${row.label}` : ""}
          </Typography>
        ))}
        {canEdit ? (
          <Stack
            component="form"
            direction="row"
            spacing={1}
            sx={{ mt: 1 }}
            onSubmit={(e) => {
              e.preventDefault();
              void post(
                `/dms/documents/${id}/link/`,
                { target: linkTarget, label: linkLabel },
                "Link added"
              );
            }}
          >
            <TextField
              select
              size="small"
              label="Document"
              value={linkTarget}
              onChange={(e) => setLinkTarget(e.target.value)}
              sx={{ minWidth: 220 }}
            >
              {docs.map((d) => (
                <MenuItem key={d.id} value={d.id}>
                  {d.name || d.id}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              size="small"
              label="Label"
              value={linkLabel}
              onChange={(e) => setLinkLabel(e.target.value)}
            />
            <Button type="submit" variant="outlined" disabled={!linkTarget}>
              Link
            </Button>
          </Stack>
        ) : null}
      </Paper>

      <Paper variant="outlined" sx={{ p: 2 }}>
        <Typography variant="subtitle1" sx={{ mb: 1 }}>
          Web links
        </Typography>
        {webLinks.map((row) => (
          <Typography key={row.id} variant="body2">
            <MuiLink href={row.url} target="_blank" rel="noopener noreferrer">
              {row.label}
            </MuiLink>
          </Typography>
        ))}
        {canEdit ? (
          <Stack
            component="form"
            direction="row"
            spacing={1}
            sx={{ mt: 1 }}
            onSubmit={(e) => {
              e.preventDefault();
              void post(
                `/dms/documents/${id}/web-link/`,
                { label: webLabel, url: webUrl },
                "Web link added"
              );
            }}
          >
            <TextField
              size="small"
              label="Label"
              value={webLabel}
              onChange={(e) => setWebLabel(e.target.value)}
            />
            <TextField
              size="small"
              label="URL"
              value={webUrl}
              onChange={(e) => setWebUrl(e.target.value)}
              sx={{ minWidth: 280 }}
            />
            <Button type="submit" variant="outlined" disabled={!webLabel.trim() || !webUrl.trim()}>
              Add
            </Button>
          </Stack>
        ) : null}
      </Paper>

      <Paper variant="outlined" sx={{ p: 2 }}>
        <Typography variant="subtitle1" sx={{ mb: 1 }}>
          Access
        </Typography>
        {access.map((row) => (
          <Typography key={row.id} variant="body2">
            {row.username} · {row.can_change ? "can edit" : "can view"}
          </Typography>
        ))}
        {canEdit && users.length ? (
          <Stack
            component="form"
            direction="row"
            spacing={1}
            sx={{ mt: 1 }}
            onSubmit={(e) => {
              e.preventDefault();
              void post(
                `/dms/documents/${id}/grant-access/`,
                { user: accessUser, can_change: true },
                "Access granted"
              );
            }}
          >
            <TextField
              select
              size="small"
              label="User"
              value={accessUser}
              onChange={(e) => setAccessUser(e.target.value)}
              sx={{ minWidth: 220 }}
            >
              {users.map((u) => (
                <MenuItem key={u.id} value={u.id}>
                  {u.username || u.email || u.id}
                </MenuItem>
              ))}
            </TextField>
            <Button type="submit" variant="outlined" disabled={!accessUser}>
              Grant edit
            </Button>
          </Stack>
        ) : null}
      </Paper>
    </Stack>
  );
}
