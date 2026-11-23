"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  Badge,
  Box,
  Button,
  Divider,
  IconButton,
  List,
  ListItemButton,
  ListItemText,
  Popover,
  Stack,
  Tooltip,
  Typography,
  Chip,
} from "@mui/material";
import NotificationsNoneOutlinedIcon from "@mui/icons-material/NotificationsNoneOutlined";
import SupportAgentIcon from "@mui/icons-material/SupportAgent";
import ReceiptLongIcon from "@mui/icons-material/ReceiptLong";
import WarningAmberIcon from "@mui/icons-material/WarningAmber";
import RefreshIcon from "@mui/icons-material/Refresh";
import DoneAllIcon from "@mui/icons-material/DoneAll";
import ChatBubbleOutlineIcon from "@mui/icons-material/ChatBubbleOutlineOutlined";
import TaskAltIcon from "@mui/icons-material/TaskAlt";
import AccountTreeOutlinedIcon from "@mui/icons-material/AccountTreeOutlined";
import api from "@/lib/api";
import { usePlatformCaps } from "@/hooks/usePlatformCaps";
import { useAppSelector } from "@/store/hooks";

type NotifItem = {
  id: string;
  kind: string;
  title: string;
  body: string;
  href: string;
  created_at?: string | null;
  source_stamp?: string;
  severity?: string;
  read?: boolean;
};

type InboxResponse = {
  count: number;
  unread: number;
  items: NotifItem[];
};

function kindIcon(kind: string, severity?: string) {
  if (kind === "billing" || severity === "urgent") {
    return <WarningAmberIcon fontSize="small" color="warning" />;
  }
  if (kind === "support") {
    return <SupportAgentIcon fontSize="small" color="primary" />;
  }
  if (kind === "comment") {
    return <ChatBubbleOutlineIcon fontSize="small" color="primary" />;
  }
  if (kind === "task") {
    return <TaskAltIcon fontSize="small" color="primary" />;
  }
  if (kind === "workflow") {
    return <AccountTreeOutlinedIcon fontSize="small" color="primary" />;
  }
  return <ReceiptLongIcon fontSize="small" color="action" />;
}

export default function HeaderNotifications() {
  const access = useAppSelector((s) => s.auth.access);
  const { isPlatformUser } = usePlatformCaps();
  const [anchor, setAnchor] = useState<HTMLElement | null>(null);
  const [items, setItems] = useState<NotifItem[]>([]);
  const [unread, setUnread] = useState(0);
  const [loading, setLoading] = useState(false);
  const [marking, setMarking] = useState(false);

  const applyInbox = (data: InboxResponse) => {
    setItems(data.items || []);
    setUnread(data.unread ?? 0);
  };

  const load = useCallback(async () => {
    if (!access && !localStorage.getItem("access_token")) return;
    setLoading(true);
    try {
      const { data } = await api.get<InboxResponse>("/notifications/");
      applyInbox(data);
    } catch {
      /* silent */
    } finally {
      setLoading(false);
    }
  }, [access]);

  useEffect(() => {
    load();
    const t = setInterval(load, 60_000);
    return () => clearInterval(t);
  }, [load]);

  const markRead = async (ids: string[], opts?: { all?: boolean }) => {
    setMarking(true);
    try {
      const { data } = await api.post<InboxResponse>("/notifications/mark-read/", {
        ids,
        all: !!opts?.all,
      });
      applyInbox(data);
    } catch {
      /* optimistic local fallback */
      if (opts?.all) {
        setItems((prev) => prev.map((it) => ({ ...it, read: true })));
        setUnread(0);
      } else {
        setItems((prev) =>
          prev.map((it) => (ids.includes(it.id) ? { ...it, read: true } : it))
        );
        setUnread((n) => Math.max(0, n - ids.length));
      }
    } finally {
      setMarking(false);
    }
  };

  const onItemClick = async (item: NotifItem) => {
    setAnchor(null);
    if (!item.read) {
      await markRead([item.id]);
    }
  };

  const open = Boolean(anchor);
  const supportHref = isPlatformUser ? "/platform/tickets" : "/support";

  return (
    <>
      <Tooltip title={unread ? `${unread} unread` : "Notifications"}>
        <IconButton
          color="inherit"
          aria-label="Notifications"
          onClick={(e) => {
            setAnchor(e.currentTarget);
            load();
          }}
          size="small"
          sx={{ mx: 0.25 }}
        >
          <Badge
            badgeContent={unread > 99 ? "99+" : unread}
            color="error"
            max={99}
            invisible={unread === 0}
          >
            <NotificationsNoneOutlinedIcon />
          </Badge>
        </IconButton>
      </Tooltip>

      <Popover
        open={open}
        anchorEl={anchor}
        onClose={() => setAnchor(null)}
        anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
        transformOrigin={{ vertical: "top", horizontal: "right" }}
        slotProps={{
          paper: {
            sx: {
              width: { xs: "min(100vw - 24px, 380px)", sm: 380 },
              maxHeight: 480,
              mt: 1,
              overflow: "hidden",
              display: "flex",
              flexDirection: "column",
            },
          },
        }}
      >
        <Stack
          direction="row"
          alignItems="center"
          justifyContent="space-between"
          sx={{ px: 2, py: 1.25 }}
        >
          <Typography fontWeight={700}>Notifications</Typography>
          <Stack direction="row" spacing={0.5} alignItems="center">
            {unread > 0 ? (
              <Chip size="small" color="error" label={`${unread} unread`} />
            ) : (
              <Chip size="small" variant="outlined" label="All read" />
            )}
            <Tooltip title="Mark all read">
              <span>
                <IconButton
                  size="small"
                  disabled={marking || unread === 0}
                  onClick={() => markRead([], { all: true })}
                  aria-label="Mark all read"
                >
                  <DoneAllIcon fontSize="small" />
                </IconButton>
              </span>
            </Tooltip>
            <IconButton size="small" onClick={load} disabled={loading} aria-label="Refresh">
              <RefreshIcon fontSize="small" />
            </IconButton>
          </Stack>
        </Stack>
        <Divider />
        <Box sx={{ overflow: "auto", flex: 1 }}>
          {items.length === 0 ? (
            <Box sx={{ p: 3, textAlign: "center" }}>
              <Typography color="text.secondary" variant="body2">
                {loading ? "Loading…" : "You're all caught up."}
              </Typography>
            </Box>
          ) : (
            <List dense disablePadding>
              {items.map((item) => {
                const isUnread = !item.read;
                return (
                  <ListItemButton
                    key={item.id}
                    component={Link}
                    href={item.href}
                    onClick={() => onItemClick(item)}
                    alignItems="flex-start"
                    sx={{
                      py: 1.25,
                      gap: 1,
                      bgcolor: isUnread ? "action.hover" : "transparent",
                      borderLeft: "3px solid",
                      borderColor: isUnread ? "primary.main" : "transparent",
                    }}
                  >
                    <Box sx={{ mt: 0.35 }}>{kindIcon(item.kind, item.severity)}</Box>
                    <ListItemText
                      primary={
                        <Stack direction="row" spacing={1} alignItems="center">
                          <Typography
                            variant="body2"
                            fontWeight={isUnread ? 700 : 500}
                            noWrap
                            sx={{ flex: 1 }}
                          >
                            {item.title}
                          </Typography>
                          {isUnread ? (
                            <Box
                              sx={{
                                width: 8,
                                height: 8,
                                borderRadius: "50%",
                                bgcolor: "primary.main",
                                flexShrink: 0,
                              }}
                            />
                          ) : null}
                          {item.severity === "urgent" || item.severity === "high" ? (
                            <Chip
                              size="small"
                              label={item.severity}
                              color={item.severity === "urgent" ? "error" : "warning"}
                              sx={{ height: 20, fontSize: 10 }}
                            />
                          ) : null}
                        </Stack>
                      }
                      secondary={
                        <Typography variant="caption" color="text.secondary" component="span">
                          {item.body}
                          {item.created_at
                            ? ` · ${new Date(item.created_at).toLocaleString()}`
                            : ""}
                          {item.read ? " · read" : ""}
                        </Typography>
                      }
                    />
                  </ListItemButton>
                );
              })}
            </List>
          )}
        </Box>
        <Divider />
        <Stack direction="row" spacing={1} sx={{ p: 1.25 }}>
          <Button
            fullWidth
            size="small"
            component={Link}
            href="/inbox"
            onClick={() => setAnchor(null)}
          >
            Inbox
          </Button>
          <Button
            fullWidth
            size="small"
            component={Link}
            href={supportHref}
            onClick={() => setAnchor(null)}
            startIcon={<SupportAgentIcon />}
          >
            Support
          </Button>
          <Button
            fullWidth
            size="small"
            variant="outlined"
            component={Link}
            href={isPlatformUser ? "/platform/invoices" : "/billing"}
            onClick={() => setAnchor(null)}
          >
            Billing
          </Button>
        </Stack>
      </Popover>
    </>
  );
}
