"use client";

import { ReactNode } from "react";
import {
  Box,
  Button,
  Checkbox,
  CircularProgress,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Toolbar,
  Typography,
} from "@mui/material";

const stickyActionsSx = {
  width: 64,
  minWidth: 64,
  position: "sticky" as const,
  right: 0,
  zIndex: 2,
  bgcolor: "background.paper",
  borderLeft: "1px solid",
  borderColor: "divider",
};
import AddIcon from "@mui/icons-material/Add";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutlined";
import RefreshIcon from "@mui/icons-material/Refresh";
import RowActionsMenu, { type RowActionItem } from "./RowActionsMenu";

export type CrudColumn<T> = {
  key: string;
  header: string;
  width?: number | string;
  render: (row: T) => ReactNode;
};

export type BulkAction = {
  key: string;
  label: string;
  icon?: ReactNode;
  onClick: () => void;
  danger?: boolean;
};

type Props<T extends { id: number }> = {
  title: string;
  subtitle?: string;
  rows: T[];
  columns: CrudColumn<T>[];
  loading?: boolean;
  selectedIds: number[];
  onToggleAll: (checked: boolean) => void;
  onToggleOne: (id: number, checked: boolean) => void;
  onRefresh: () => void;
  onCreate?: () => void;
  onEdit?: (row: T) => void;
  onView?: (row: T) => void;
  onDeleteOne?: (row: T) => void;
  onBulkDelete?: () => void;
  createLabel?: string;
  canCreate?: boolean;
  canEdit?: boolean;
  canDelete?: boolean;
  canSelect?: boolean;
  toolbarExtra?: ReactNode;
  emptyTitle?: string;
  emptyHint?: string;
  /** Extra per-row menu items (after Edit, before Delete). */
  getRowActions?: (row: T) => RowActionItem[];
  /** Icon shown on the row, beside the actions menu. */
  renderRowAction?: (row: T) => ReactNode;
  /** Extra bulk toolbar buttons when selection is non-empty. */
  bulkActions?: BulkAction[];
  bulkDeleteLabel?: string;
};

export default function CrudTable<T extends { id: number }>({
  title,
  subtitle,
  rows,
  columns,
  loading,
  selectedIds,
  onToggleAll,
  onToggleOne,
  onRefresh,
  onCreate,
  onEdit,
  onView,
  onDeleteOne,
  onBulkDelete,
  createLabel = "Add",
  canCreate = true,
  canEdit = true,
  canDelete = true,
  canSelect,
  toolbarExtra,
  emptyTitle = "No records yet",
  emptyHint,
  getRowActions,
  renderRowAction,
  bulkActions = [],
  bulkDeleteLabel = "Delete selected",
}: Props<T>) {
  const showSelect = canSelect ?? (canDelete || bulkActions.length > 0);
  const allSelected = rows.length > 0 && selectedIds.length === rows.length;
  const someSelected = selectedIds.length > 0 && selectedIds.length < rows.length;
  const showBulkBar = showSelect && selectedIds.length > 0;

  return (
    <Stack spacing={2.5}>
      <Stack
        direction={{ xs: "column", sm: "row" }}
        justifyContent="space-between"
        alignItems={{ xs: "stretch", sm: "flex-start" }}
        spacing={1.5}
      >
        <Box sx={{ minWidth: 0, flex: "1 1 auto" }}>
          <Typography
            variant="h4"
            sx={{ fontWeight: 650, letterSpacing: "-0.02em", lineHeight: 1.25 }}
          >
            {title}
          </Typography>
          {subtitle ? (
            <Typography
              variant="body2"
              color="text.secondary"
              sx={{ mt: 0.5, maxWidth: 520, lineHeight: 1.45 }}
            >
              {subtitle}
            </Typography>
          ) : null}
        </Box>
        <Stack
          direction="row"
          spacing={1}
          flexWrap="wrap"
          useFlexGap
          sx={{ flexShrink: 0, alignItems: "center" }}
        >
          <Button startIcon={<RefreshIcon />} onClick={onRefresh} variant="outlined">
            Refresh
          </Button>
          {canCreate && onCreate ? (
            <Button startIcon={<AddIcon />} variant="contained" onClick={onCreate}>
              {createLabel}
            </Button>
          ) : null}
        </Stack>
      </Stack>

      {toolbarExtra ? (
        <Box
          sx={{
            display: "flex",
            flexWrap: "wrap",
            gap: 1.25,
            alignItems: "center",
            width: "100%",
            "& > *": { flex: "1 1 140px", maxWidth: { xs: "100%", sm: 280 } },
            "& .MuiButton-root": { flex: "0 0 auto", maxWidth: "none" },
          }}
        >
          {toolbarExtra}
        </Box>
      ) : null}

      <Paper variant="outlined" sx={{ overflow: "hidden" }}>
        {showBulkBar ? (
          <Toolbar
            sx={{
              bgcolor: "primary.main",
              color: "primary.contrastText",
              minHeight: "52px !important",
              gap: 1,
              flexWrap: "wrap",
            }}
          >
            <Typography sx={{ flex: 1, minWidth: 120 }}>
              {selectedIds.length} selected
            </Typography>
            {bulkActions.map((a) => (
              <Button
                key={a.key}
                color="inherit"
                startIcon={a.icon}
                onClick={a.onClick}
                variant="outlined"
                sx={{ borderColor: "rgba(255,255,255,.4)" }}
              >
                {a.label}
              </Button>
            ))}
            {canDelete && onBulkDelete ? (
              <Button
                color="inherit"
                startIcon={<DeleteOutlineIcon />}
                onClick={onBulkDelete}
                sx={{ borderColor: "rgba(255,255,255,.4)" }}
                variant="outlined"
              >
                {bulkDeleteLabel}
              </Button>
            ) : null}
          </Toolbar>
        ) : null}

        {loading ? (
          <Stack alignItems="center" justifyContent="center" p={5} minHeight={180}>
            <CircularProgress />
          </Stack>
        ) : (
          <TableContainer sx={{ overflowX: "auto", maxWidth: "100%" }}>
            <Table size="small" sx={{ minWidth: columns.length > 6 ? 960 : undefined }}>
              <TableHead>
                <TableRow>
                  {showSelect ? (
                    <TableCell padding="checkbox">
                      <Checkbox
                        indeterminate={someSelected}
                        checked={allSelected}
                        onChange={(e) => onToggleAll(e.target.checked)}
                      />
                    </TableCell>
                  ) : null}
                  {columns.map((c) => (
                    <TableCell key={c.key} sx={{ width: c.width, fontWeight: 700 }}>
                      {c.header}
                    </TableCell>
                  ))}
                  <TableCell
                    align="right"
                    sx={{ ...stickyActionsSx, fontWeight: 700, zIndex: 3 }}
                  >
                    Actions
                  </TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {rows.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={columns.length + (showSelect ? 2 : 1)}>
                      <Box py={5} px={2} textAlign="center" sx={{ maxWidth: 420, mx: "auto" }}>
                        <Typography color="text.secondary" fontWeight={600}>
                          {emptyTitle}
                        </Typography>
                        <Typography
                          color="text.secondary"
                          variant="body2"
                          sx={{ mt: 0.75, lineHeight: 1.5 }}
                        >
                          {emptyHint ||
                            (canCreate
                              ? `Click “${createLabel}” to create the first one.`
                              : "Nothing to show for the current filters.")}
                        </Typography>
                      </Box>
                    </TableCell>
                  </TableRow>
                ) : (
                  rows.map((row) => {
                    const checked = selectedIds.includes(row.id);
                    return (
                      <TableRow key={row.id} hover selected={checked}>
                        {showSelect ? (
                          <TableCell padding="checkbox">
                            <Checkbox
                              checked={checked}
                              onChange={(e) => onToggleOne(row.id, e.target.checked)}
                            />
                          </TableCell>
                        ) : null}
                        {columns.map((c) => (
                          <TableCell key={c.key}>{c.render(row)}</TableCell>
                        ))}
                        <TableCell
                          align="right"
                          sx={{
                            ...stickyActionsSx,
                            width: renderRowAction ? 96 : stickyActionsSx.width,
                            minWidth: renderRowAction ? 96 : stickyActionsSx.minWidth,
                          }}
                        >
                          <Stack direction="row" spacing={0.25} justifyContent="flex-end" alignItems="center">
                            {renderRowAction?.(row)}
                          <RowActionsMenu
                            onView={onView ? () => onView(row) : undefined}
                            onEdit={canEdit && onEdit ? () => onEdit(row) : undefined}
                            onDelete={
                              canDelete && onDeleteOne ? () => onDeleteOne(row) : undefined
                            }
                            extraActions={getRowActions?.(row) || []}
                          />
                          </Stack>
                        </TableCell>
                      </TableRow>
                    );
                  })
                )}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </Paper>
    </Stack>
  );
}
