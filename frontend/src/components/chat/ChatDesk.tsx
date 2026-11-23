"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import {
  Box,
  Button,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  IconButton,
  ListItemIcon,
  ListItemText,
  Menu,
  MenuItem,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import AttachFileIcon from "@mui/icons-material/AttachFile";
import MoreVertIcon from "@mui/icons-material/MoreVert";
import NotificationsOffIcon from "@mui/icons-material/NotificationsOff";
import api from "@/lib/api";
import { getApiErrorMessage } from "@/lib/apiError";
import { useAppSelector } from "@/store/hooks";
import { useSnackbar } from "notistack";

type Person = { id: number; name: string; username: string };
type Member = {
  user_id: number;
  name: string;
  username: string;
  role: string;
  status: string;
};
type Room = {
  id: number;
  kind: string;
  name: string;
  topic: string;
  my_role: string;
  my_status: string;
  muted: boolean;
  unread: number;
  members: Member[];
  last_message: {
    id: number;
    body: string;
    sender_name: string;
    kind: string;
    created_at?: string;
    sent_label?: string;
  } | null;
};
function attachmentHref(path: string) {
  if (/^https?:/i.test(path)) return path;
  const origin = (process.env.NEXT_PUBLIC_API_URL || "").replace(/\/api\/?$/, "");
  return `${origin}${path.startsWith("/") ? path : `/${path}`}`;
}

type ChatMessage = {
  id: number;
  sender_id: number | null;
  sender_name: string;
  body: string;
  kind: string;
  removed: boolean;
  edited_at: string | null;
  created_at: string;
  sent_label?: string;
  attachment_url?: string;
  attachment_name?: string;
  attachment_kind?: string;
  reply_to: { id: number; body: string; sender_name: string } | null;
};

function messageTime(message: { created_at?: string; sent_label?: string }) {
  const raw = message.created_at || "";
  const date = raw ? new Date(raw) : null;
  if (!date || Number.isNaN(date.getTime())) return message.sent_label || "";
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${pad(date.getDate())}-${pad(date.getMonth() + 1)}-${date.getFullYear()} ${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function isImageAttachment(message: ChatMessage) {
  if (message.attachment_kind === "image") return true;
  const name = `${message.attachment_name || ""} ${message.attachment_url || ""}`.toLowerCase();
  return /\.(jpg|jpeg|png|gif|webp)(\?|$)/.test(name);
}

export default function ChatDesk() {
  const { enqueueSnackbar } = useSnackbar();
  const me = useAppSelector((s) => s.auth.user?.id);
  const params = useSearchParams();
  const [rooms, setRooms] = useState<Room[]>([]);
  const [selected, setSelected] = useState<number | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [filter, setFilter] = useState("");
  const [reply, setReply] = useState<ChatMessage | null>(null);
  const [editing, setEditing] = useState<ChatMessage | null>(null);
  const [people, setPeople] = useState<Person[]>([]);
  const [dialog, setDialog] = useState<"direct" | "group" | "invite" | "rename" | "members" | null>(null);
  const [query, setQuery] = useState("");
  const [groupName, setGroupName] = useState("");
  const [topic, setTopic] = useState("");
  const [picked, setPicked] = useState<number[]>([]);
  const [menu, setMenu] = useState<null | HTMLElement>(null);
  const [msgMenu, setMsgMenu] = useState<{ el: HTMLElement; message: ChatMessage } | null>(null);
  const roomsReq = useRef(0);
  const fileInput = useRef<HTMLInputElement | null>(null);

  const room = rooms.find((row) => row.id === selected) || null;
  const manager = room?.my_role === "owner" || room?.my_role === "admin";

  const loadRooms = useCallback(async () => {
    const token = ++roomsReq.current;
    const { data } = await api.get<Room[]>("/chat/rooms/");
    const rows = data || [];
    if (token === roomsReq.current) setRooms(rows);
    return rows;
  }, []);

  const loadMessages = useCallback(async (roomId: number) => {
    const { data } = await api.get<ChatMessage[]>(`/chat/rooms/${roomId}/messages/`);
    setMessages(data || []);
  }, []);

  useEffect(() => {
    loadRooms()
      .then((rows) => {
        const requested = Number(params.get("room") || 0);
        if (requested && rows.some((row) => row.id === requested)) setSelected(requested);
      })
      .catch((e: unknown) => enqueueSnackbar(getApiErrorMessage(e, "Chat failed to load"), { variant: "error" }));
  }, [enqueueSnackbar, loadRooms, params]);

  useEffect(() => {
    if (!selected) return;
    loadMessages(selected).catch((e: unknown) =>
      enqueueSnackbar(getApiErrorMessage(e, "Messages failed to load"), { variant: "error" })
    );
  }, [enqueueSnackbar, loadMessages, selected]);

  useEffect(() => {
    const timer = window.setInterval(() => {
      if (document.visibilityState === "hidden") return;
      loadRooms().catch(() => undefined);
      if (selected) loadMessages(selected).catch(() => undefined);
    }, 8000);
    return () => window.clearInterval(timer);
  }, [loadMessages, loadRooms, selected]);

  const visible = useMemo(() => {
    const q = filter.trim().toLowerCase();
    if (!q) return rooms;
    return rooms.filter((row) => row.name.toLowerCase().includes(q));
  }, [filter, rooms]);

  const searchPeople = async (value: string) => {
    setQuery(value);
    const { data } = await api.get<Person[]>("/chat/people/", { params: { q: value } });
    setPeople(data || []);
  };

  const openDialog = (next: typeof dialog) => {
    setDialog(next);
    setQuery("");
    setPicked([]);
    setPeople([]);
    if (next === "rename" && room) {
      setGroupName(room.name);
      setTopic(room.topic || "");
    }
    if (next === "group") {
      setGroupName("");
      setTopic("");
    }
    if (next === "direct" || next === "invite" || next === "group") void searchPeople("");
  };

  const fail = (e: unknown) => enqueueSnackbar(getApiErrorMessage(e, "Chat action failed"), { variant: "error" });

  const chooseRoom = async (row: Room) => {
    setSelected(row.id);
    setReply(null);
    setEditing(null);
    if (row.my_status === "active") {
      try {
        await loadMessages(row.id);
        await loadRooms();
      } catch (e: unknown) {
        fail(e);
      }
    }
  };

  const send = async () => {
    if (!room || room.my_status !== "active") return;
    const body = draft.trim();
    if (!body && !file) return;
    if (file && file.size > 8 * 1024 * 1024) {
      enqueueSnackbar("Attachments must be 8 MB or smaller.", { variant: "warning" });
      return;
    }
    try {
      if (editing) {
        await api.patch(`/chat/messages/${editing.id}/`, { body });
        setEditing(null);
      } else if (file) {
        const payload = new FormData();
        payload.append("body", body);
        payload.append("attachment", file);
        if (reply?.id) payload.append("reply_to", String(reply.id));
        await api.post(`/chat/rooms/${room.id}/messages/`, payload, {
          transformRequest: [
            (form, headers) => {
              if (headers) delete headers["Content-Type"];
              return form;
            },
          ],
        });
        setReply(null);
        setFile(null);
        if (fileInput.current) fileInput.current.value = "";
      } else {
        await api.post(`/chat/rooms/${room.id}/messages/`, {
          body,
          reply_to: reply?.id || null,
        });
        setReply(null);
      }
      setDraft("");
      await loadMessages(room.id);
      await loadRooms();
    } catch (e: unknown) {
      fail(e);
    }
  };

  const createDirect = async (person: Person) => {
    try {
      const { data } = await api.post<Room>("/chat/direct/", { user_id: person.id });
      setDialog(null);
      await loadRooms();
      setSelected(data.id);
    } catch (e: unknown) {
      fail(e);
    }
  };

  const createGroup = async () => {
    if (!groupName.trim()) return;
    try {
      const { data } = await api.post<Room>("/chat/rooms/", {
        name: groupName.trim(),
        topic: topic.trim(),
        user_ids: picked,
      });
      setDialog(null);
      await loadRooms();
      setSelected(data.id);
    } catch (e: unknown) {
      fail(e);
    }
  };

  const invite = async () => {
    if (!room || picked.length === 0) return;
    try {
      await api.post(`/chat/rooms/${room.id}/invite/`, { user_ids: picked });
      setDialog(null);
      await loadRooms();
    } catch (e: unknown) {
      fail(e);
    }
  };

  const act = async (path: string, body?: unknown) => {
    const muting = path.endsWith("/mute/") && room;
    const nextMuted = muting ? !room.muted : room?.muted;
    if (muting) {
      setRooms((prev) => prev.map((row) => (row.id === room.id ? { ...row, muted: Boolean(nextMuted) } : row)));
      setMenu(null);
    }
    try {
      const { data } = await api.post<Room>(path, body || {});
      if (data && typeof data.id === "number") {
        setRooms((prev) => prev.map((row) => (row.id === data.id ? { ...row, ...data } : row)));
      }
      setMenu(null);
      const rows = await loadRooms();
      if (!rows.some((row) => row.id === selected)) setSelected(null);
      else if (selected) await loadMessages(selected);
    } catch (e: unknown) {
      if (muting) {
        setRooms((prev) => prev.map((row) => (row.id === room.id ? { ...row, muted: room.muted } : row)));
      }
      fail(e);
    }
  };

  const memberIds = new Set((room?.members || []).map((row) => row.user_id));

  return (
    <Stack spacing={1} sx={{ height: "calc(100vh - 150px)", minHeight: 480 }}>
      <Box>
        <Typography variant="h5" fontWeight={700}>
          Chat
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Direct messages and groups stay inside this organization.
        </Typography>
      </Box>
      <Stack direction="row" spacing={1} sx={{ flex: 1, minHeight: 0 }}>
        <Stack spacing={1} sx={{ width: 320, minWidth: 260 }}>
          <Stack direction="row" spacing={1}>
            <Button size="small" variant="outlined" onClick={() => openDialog("direct")}>
              Direct
            </Button>
            <Button size="small" variant="contained" onClick={() => openDialog("group")}>
              New group
            </Button>
          </Stack>
          <TextField
            size="small"
            placeholder="Search conversations"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
          />
          <Box sx={{ overflow: "auto", flex: 1 }}>
            {visible.length === 0 ? (
              <Typography color="text.secondary" variant="body2" sx={{ p: 1 }}>
                No conversations yet.
              </Typography>
            ) : null}
            {visible.map((row) => {
              const stamp = row.last_message?.sent_label || (row.last_message ? messageTime(row.last_message) : "");
              return (
              <Box
                key={row.id}
                onClick={() => void chooseRoom(row)}
                sx={{
                  p: 1.25,
                  mb: 0.5,
                  borderRadius: 1,
                  cursor: "pointer",
                  bgcolor: row.id === selected ? "action.selected" : "transparent",
                  "&:hover": { bgcolor: "action.hover" },
                }}
              >
                <Stack direction="row" spacing={1} alignItems="center">
                  <Typography fontWeight={row.unread ? 700 : 500} sx={{ flex: 1, minWidth: 0 }} noWrap>
                    {row.name}
                  </Typography>
                  {row.muted ? (
                    <NotificationsOffIcon fontSize="small" color="warning" titleAccess="Muted" aria-label="Muted" />
                  ) : null}
                  {row.my_status === "invited" ? <Chip size="small" label="Invite" color="primary" /> : null}
                  {row.unread > 0 ? <Chip size="small" label={row.unread} color="secondary" /> : null}
                </Stack>
                <Typography variant="caption" color="text.secondary" noWrap>
                  {row.kind === "group" ? "Group" : "Direct"}
                  {stamp ? ` · ${stamp}` : ""}
                  {row.last_message?.body ? ` · ${row.last_message.body}` : ""}
                </Typography>
                {row.my_status === "invited" ? (
                  <Stack direction="row" spacing={1} sx={{ mt: 0.5 }}>
                    <Button size="small" onClick={(e) => { e.stopPropagation(); void act(`/chat/rooms/${row.id}/accept/`); }}>
                      Accept
                    </Button>
                    <Button size="small" color="inherit" onClick={(e) => { e.stopPropagation(); void act(`/chat/rooms/${row.id}/decline/`); }}>
                      Decline
                    </Button>
                  </Stack>
                ) : null}
              </Box>
              );
            })}
          </Box>
        </Stack>
        <Stack sx={{ flex: 1, minWidth: 0, border: "1px solid", borderColor: "divider", borderRadius: 1 }}>
          {!room ? (
            <Stack alignItems="center" justifyContent="center" sx={{ flex: 1 }}>
              <Typography color="text.secondary">Select a conversation or start one.</Typography>
            </Stack>
          ) : (
            <>
              <Stack direction="row" alignItems="center" sx={{ px: 2, py: 1, borderBottom: "1px solid", borderColor: "divider" }}>
                <Box sx={{ flex: 1, minWidth: 0 }}>
                  <Stack direction="row" spacing={0.75} alignItems="center">
                    <Typography fontWeight={700} noWrap sx={{ minWidth: 0 }}>{room.name}</Typography>
                    {room.muted ? (
                      <Chip
                        size="small"
                        color="warning"
                        variant="outlined"
                        icon={<NotificationsOffIcon />}
                        label="Muted"
                        aria-label="Muted"
                      />
                    ) : null}
                  </Stack>
                  <Typography variant="caption" color="text.secondary" noWrap>
                    {room.topic || `${room.members.filter((m) => m.status === "active").length} active`}
                  </Typography>
                </Box>
                <IconButton aria-label="conversation actions" onClick={(e) => setMenu(e.currentTarget)}>
                  <MoreVertIcon />
                </IconButton>
              </Stack>
              <Box sx={{ flex: 1, overflow: "auto", px: 2, py: 1 }}>
                {room.my_status === "invited" ? (
                  <Typography color="text.secondary">Accept the invite to read and send messages.</Typography>
                ) : (
                  messages.map((message) => (
                    <Box key={message.id} sx={{ py: 0.75, textAlign: message.kind === "system" ? "center" : "left" }}>
                      {message.kind === "system" ? (
                        <Typography variant="caption" color="text.secondary">
                          {message.body}
                          {messageTime(message) ? ` · ${messageTime(message)}` : ""}
                        </Typography>
                      ) : (
                        <Stack direction="row" justifyContent={message.sender_id === me ? "flex-end" : "flex-start"}>
                          <Box sx={{ maxWidth: "75%", bgcolor: message.sender_id === me ? "action.selected" : "background.paper", border: "1px solid", borderColor: "divider", borderRadius: 1, px: 1.25, py: 0.75 }}>
                            <Stack direction="row" spacing={1} alignItems="center">
                              <Typography variant="caption" fontWeight={700}>{message.sender_name}</Typography>
                              <Typography variant="caption" color="text.secondary" sx={{ ml: "auto", whiteSpace: "nowrap" }}>
                                {messageTime(message)}
                              </Typography>
                              <IconButton size="small" aria-label="message actions" onClick={(e) => setMsgMenu({ el: e.currentTarget, message })}>
                                <MoreVertIcon fontSize="small" />
                              </IconButton>
                            </Stack>
                            {message.reply_to ? (
                              <Typography variant="caption" color="text.secondary" display="block">
                                {message.reply_to.sender_name}: {message.reply_to.body}
                              </Typography>
                            ) : null}
                            <Typography variant="body2" sx={{ whiteSpace: "pre-wrap" }}>
                              {message.removed ? "Message removed" : message.body}
                            </Typography>
                            {message.edited_at && !message.removed ? (
                              <Typography variant="caption" color="text.secondary" sx={{ display: "block" }}>Edited</Typography>
                            ) : null}
                            {message.attachment_url && !message.removed && isImageAttachment(message) ? (
                              <Box
                                component="a"
                                href={attachmentHref(message.attachment_url)}
                                target="_blank"
                                rel="noreferrer"
                                sx={{ display: "block", mt: 0.75 }}
                              >
                                <Box
                                  component="img"
                                  src={attachmentHref(message.attachment_url)}
                                  alt={message.attachment_name || "Picture"}
                                  sx={{ display: "block", maxWidth: "100%", maxHeight: 240, borderRadius: 1 }}
                                />
                              </Box>
                            ) : null}
                            {message.attachment_url && !message.removed && !isImageAttachment(message) ? (
                              <Typography
                                variant="body2"
                                component="a"
                                href={attachmentHref(message.attachment_url)}
                                target="_blank"
                                rel="noreferrer"
                                sx={{ display: "block", mt: 0.75 }}
                              >
                                {message.attachment_name || "Open document"}
                              </Typography>
                            ) : null}
                          </Box>
                        </Stack>
                      )}
                    </Box>
                  ))
                )}
              </Box>
              {room.my_status === "active" ? (
                <Stack spacing={0.5} sx={{ p: 1.5, borderTop: "1px solid", borderColor: "divider" }}>
                  {reply ? (
                    <Typography variant="caption">Replying to {reply.sender_name}</Typography>
                  ) : null}
                  {editing ? <Typography variant="caption">Editing your message</Typography> : null}
                  {file ? (
                    <Stack direction="row" spacing={1} alignItems="center">
                      <Typography variant="caption" color="text.secondary">
                        {file.name}
                      </Typography>
                      <Button size="small" color="inherit" onClick={() => { setFile(null); if (fileInput.current) fileInput.current.value = ""; }}>
                        Remove
                      </Button>
                    </Stack>
                  ) : null}
                  <Stack direction="row" spacing={1} alignItems="flex-end">
                    <input
                      ref={fileInput}
                      id="chat-attachment"
                      type="file"
                      hidden
                      accept="image/*,.pdf,.doc,.docx,.xls,.xlsx,.txt,.csv"
                      onChange={(event) => setFile(event.target.files?.[0] || null)}
                    />
                    <Button
                      size="small"
                      variant="outlined"
                      startIcon={<AttachFileIcon />}
                      aria-label="Attach a picture or document"
                      onClick={() => fileInput.current?.click()}
                      sx={{ whiteSpace: "nowrap" }}
                    >
                      Attach
                    </Button>
                    <TextField
                      fullWidth
                      size="small"
                      multiline
                      maxRows={4}
                      placeholder="Write a message"
                      value={draft}
                      onChange={(e) => setDraft(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" && !e.shiftKey) {
                          e.preventDefault();
                          void send();
                        }
                      }}
                    />
                    <Button variant="contained" onClick={() => void send()}>
                      Send
                    </Button>
                  </Stack>
                </Stack>
              ) : null}
            </>
          )}
        </Stack>
      </Stack>

      <Menu anchorEl={menu} open={Boolean(menu)} onClose={() => setMenu(null)}>
        {room?.kind === "group" && manager ? (
          <MenuItem onClick={() => { setMenu(null); openDialog("invite"); }}>
            <ListItemText>Invite</ListItemText>
          </MenuItem>
        ) : null}
        {room?.kind === "group" && manager ? (
          <MenuItem onClick={() => { setMenu(null); openDialog("rename"); }}>
            <ListItemText>Rename</ListItemText>
          </MenuItem>
        ) : null}
        <MenuItem onClick={() => { setMenu(null); openDialog("members"); }}>
          <ListItemText>Members</ListItemText>
        </MenuItem>
        {room?.my_status === "active" ? (
          <MenuItem onClick={() => void act(`/chat/rooms/${room.id}/mute/`, { muted: !room.muted })}>
            <ListItemText>{room.muted ? "Unmute" : "Mute"}</ListItemText>
          </MenuItem>
        ) : null}
        <MenuItem onClick={() => room && void act(`/chat/rooms/${room.id}/leave/`)}>
          <ListItemText primaryTypographyProps={{ color: "error" }}>Leave</ListItemText>
        </MenuItem>
      </Menu>

      <Menu anchorEl={msgMenu?.el} open={Boolean(msgMenu)} onClose={() => setMsgMenu(null)}>
        <MenuItem onClick={() => { setReply(msgMenu?.message || null); setEditing(null); setMsgMenu(null); }}>
          <ListItemIcon />
          <ListItemText>Reply</ListItemText>
        </MenuItem>
        {msgMenu && msgMenu.message.sender_id === me && !msgMenu.message.removed ? (
          <MenuItem onClick={() => { setEditing(msgMenu.message); setDraft(msgMenu.message.body); setReply(null); setMsgMenu(null); }}>
            <ListItemText>Edit</ListItemText>
          </MenuItem>
        ) : null}
        {msgMenu && !msgMenu.message.removed && (msgMenu.message.sender_id === me || manager) ? (
          <MenuItem onClick={() => { void act(`/chat/messages/${msgMenu.message.id}/remove/`); setMsgMenu(null); }}>
            <ListItemText primaryTypographyProps={{ color: "error" }}>Remove</ListItemText>
          </MenuItem>
        ) : null}
      </Menu>

      <Dialog open={dialog === "direct" || dialog === "group" || dialog === "invite"} onClose={() => setDialog(null)} fullWidth>
        <DialogTitle>{dialog === "group" ? "New group" : dialog === "invite" ? "Invite colleagues" : "Direct message"}</DialogTitle>
        <DialogContent>
          {dialog === "group" ? (
            <Stack spacing={1} sx={{ mt: 1 }}>
              <TextField label="Group name" value={groupName} onChange={(e) => setGroupName(e.target.value)} />
              <TextField label="Topic" value={topic} onChange={(e) => setTopic(e.target.value)} />
            </Stack>
          ) : null}
          <TextField sx={{ mt: 1 }} fullWidth size="small" placeholder="Search colleagues" value={query} onChange={(e) => void searchPeople(e.target.value)} />
          <Stack sx={{ mt: 1, maxHeight: 280, overflow: "auto" }}>
            {people.filter((person) => dialog !== "invite" || !memberIds.has(person.id)).map((person) => (
              <Button
                key={person.id}
                sx={{ justifyContent: "flex-start" }}
                variant={picked.includes(person.id) ? "contained" : "text"}
                onClick={() => {
                  if (dialog === "direct") void createDirect(person);
                  else setPicked((curr) => curr.includes(person.id) ? curr.filter((id) => id !== person.id) : [...curr, person.id]);
                }}
              >
                {person.name} · {person.username}
              </Button>
            ))}
          </Stack>
        </DialogContent>
        {dialog === "direct" ? null : (
          <DialogActions>
            <Button onClick={() => setDialog(null)}>Cancel</Button>
            <Button variant="contained" onClick={() => void (dialog === "group" ? createGroup() : invite())}>
              {dialog === "group" ? "Create" : "Invite"}
            </Button>
          </DialogActions>
        )}
      </Dialog>

      <Dialog open={dialog === "rename"} onClose={() => setDialog(null)} fullWidth>
        <DialogTitle>Rename group</DialogTitle>
        <DialogContent>
          <Stack spacing={1} sx={{ mt: 1 }}>
            <TextField label="Name" value={groupName} onChange={(e) => setGroupName(e.target.value)} />
            <TextField label="Topic" value={topic} onChange={(e) => setTopic(e.target.value)} />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialog(null)}>Cancel</Button>
          <Button
            variant="contained"
            onClick={() => {
              if (!room) return;
              void api.patch(`/chat/rooms/${room.id}/`, { name: groupName, topic }).then(() => loadRooms()).then(() => setDialog(null)).catch(fail);
            }}
          >
            Save
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={dialog === "members"} onClose={() => setDialog(null)} fullWidth>
        <DialogTitle>Members</DialogTitle>
        <DialogContent>
          {(room?.members || []).map((member) => (
            <Stack key={member.user_id} direction="row" alignItems="center" spacing={1} sx={{ py: 0.5 }}>
              <Box sx={{ flex: 1 }}>
                <Typography>{member.name}</Typography>
                <Typography variant="caption" color="text.secondary">{member.username} · {member.role} · {member.status}</Typography>
              </Box>
              {room?.my_role === "owner" && member.status === "active" && member.user_id !== me && member.role !== "owner" ? (
                <Button size="small" onClick={() => void act(`/chat/rooms/${room.id}/members/${member.user_id}/role/`, { role: member.role === "admin" ? "member" : "admin" })}>
                  {member.role === "admin" ? "Make member" : "Make admin"}
                </Button>
              ) : null}
              {manager && member.user_id !== me && member.role !== "owner" && member.status !== "removed" ? (
                <Button size="small" color="error" onClick={() => room && void act(`/chat/rooms/${room.id}/members/${member.user_id}/remove/`)}>
                  Remove
                </Button>
              ) : null}
            </Stack>
          ))}
        </DialogContent>
      </Dialog>
    </Stack>
  );
}
