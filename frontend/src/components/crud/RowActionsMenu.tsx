"use client";

import { Fragment, useState, type ReactNode } from "react";
import { Divider, IconButton, ListItemIcon, ListItemText, Menu, MenuItem } from "@mui/material";
import MoreVertIcon from "@mui/icons-material/MoreVert";
import EditOutlinedIcon from "@mui/icons-material/EditOutlined";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutlined";
import VisibilityOutlinedIcon from "@mui/icons-material/VisibilityOutlined";

export type RowActionItem = {
  key: string;
  label: string;
  icon?: ReactNode;
  onClick: () => void;
  disabled?: boolean;
  danger?: boolean;
  dividerBefore?: boolean;
};

type Props = {
  onView?: () => void;
  onEdit?: () => void;
  onDelete?: () => void;
  disableEdit?: boolean;
  disableDelete?: boolean;
  extraActions?: RowActionItem[];
};

export default function RowActionsMenu({
  onView,
  onEdit,
  onDelete,
  disableEdit,
  disableDelete,
  extraActions = [],
}: Props) {
  const [anchor, setAnchor] = useState<null | HTMLElement>(null);
  const open = Boolean(anchor);
  const close = () => setAnchor(null);

  const hasAny =
    !!onView || !!onEdit || !!onDelete || extraActions.some((a) => a);

  if (!hasAny) return null;

  return (
    <>
      <IconButton
        size="small"
        aria-label="row actions"
        onClick={(e) => {
          e.stopPropagation();
          setAnchor(e.currentTarget);
        }}
      >
        <MoreVertIcon fontSize="small" />
      </IconButton>
      <Menu
        anchorEl={anchor}
        open={open}
        onClose={close}
        anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
        transformOrigin={{ vertical: "top", horizontal: "right" }}
      >
        {onView ? (
          <MenuItem
            onClick={() => {
              close();
              onView();
            }}
          >
            <ListItemIcon>
              <VisibilityOutlinedIcon fontSize="small" />
            </ListItemIcon>
            <ListItemText>View</ListItemText>
          </MenuItem>
        ) : null}
        {onEdit ? (
          <MenuItem
            disabled={disableEdit}
            onClick={() => {
              close();
              onEdit();
            }}
          >
            <ListItemIcon>
              <EditOutlinedIcon fontSize="small" />
            </ListItemIcon>
            <ListItemText>Edit</ListItemText>
          </MenuItem>
        ) : null}
        {extraActions.map((action) => (
          <Fragment key={action.key}>
            {action.dividerBefore ? <Divider /> : null}
            <MenuItem
              disabled={action.disabled}
              onClick={() => {
                close();
                action.onClick();
              }}
            >
              {action.icon ? <ListItemIcon>{action.icon}</ListItemIcon> : null}
              <ListItemText
                primaryTypographyProps={
                  action.danger ? { color: "error" } : undefined
                }
              >
                {action.label}
              </ListItemText>
            </MenuItem>
          </Fragment>
        ))}
        {onDelete ? (
          <MenuItem
            disabled={disableDelete}
            onClick={() => {
              close();
              onDelete();
            }}
          >
            <ListItemIcon>
              <DeleteOutlineIcon fontSize="small" color="error" />
            </ListItemIcon>
            <ListItemText>Delete</ListItemText>
          </MenuItem>
        ) : null}
      </Menu>
    </>
  );
}
