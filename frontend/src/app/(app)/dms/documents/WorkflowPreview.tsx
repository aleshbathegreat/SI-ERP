"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import {
  Background,
  Controls,
  Handle,
  MarkerType,
  Position,
  ReactFlow,
  applyNodeChanges,
  type Edge,
  type Node,
  type NodeChange,
  type NodeProps,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useTheme } from "@mui/material/styles";
import {
  Box,
  Button,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
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
import api from "@/lib/api";
import { useRecordAction } from "@/hooks/useRecordAction";
import { formatDate } from "@/lib/format";

type PreviewState = {
  id: number;
  name: string;
  is_initial?: boolean;
  is_terminal?: boolean;
  escalation_hours?: number | null;
  document_status?: string;
  escalate_to_id?: number | null;
  escalate_to_name?: string;
};
type PreviewTransition = {
  id: number;
  label: string;
  from_state_id?: number;
  to_state_id?: number;
  from_name: string;
  to_name: string;
  require_signature?: boolean;
  require_comment?: boolean;
  block_self_approval?: boolean;
  roles?: string[];
  events?: string[];
  actions?: { action_type: string }[];
};
type PreviewTrigger = {
  id: number;
  event: string;
  state_name?: string;
  actions?: { action_type: string }[];
};
export type WorkflowPreviewData = {
  states?: PreviewState[];
  transitions?: PreviewTransition[];
  triggers?: PreviewTrigger[];
};

const CIRCLE = 128;
const LAYOUT_KEY = "sierp-workflow-circles";

type StateNodeData = {
  label: string;
  caption: string;
  extra: string;
  current: boolean;
  terminal: boolean;
  initial: boolean;
};

function edgeCaption(row: PreviewTransition) {
  return row.label.length > 28 ? `${row.label.slice(0, 26)}…` : row.label;
}

function xml(value: string) {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function fileSlug(title: string) {
  const slug = title.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
  return slug || "workflow";
}

function circleCenter(node: Node) {
  return { x: node.position.x + CIRCLE / 2, y: node.position.y + CIRCLE / 2 };
}

function diagramSvg(title: string, nodes: Node[], edges: Edge[]) {
  const centers = new Map(nodes.map((node) => [node.id, circleCenter(node)]));
  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  nodes.forEach((node) => {
    minX = Math.min(minX, node.position.x);
    minY = Math.min(minY, node.position.y);
    maxX = Math.max(maxX, node.position.x + CIRCLE);
    maxY = Math.max(maxY, node.position.y + CIRCLE);
  });
  minX -= 48;
  minY -= 64;
  maxX += 48;
  maxY += 64;
  const width = Math.max(320, maxX - minX);
  const height = Math.max(220, maxY - minY);
  const sx = (value: number) => value - minX;
  const sy = (value: number) => value - minY;
  const paths = edges.flatMap((edge) => {
    const from = centers.get(edge.source);
    const to = centers.get(edge.target);
    if (!from || !to) return [];
    const dashed = String(edge.id).startsWith("esc");
    const back = !dashed && to.x + 16 < from.x;
    const r = CIRCLE / 2;
    let d = "";
    let lx = 0;
    let ly = 0;
    if (back || dashed) {
      const y = dashed ? Math.min(from.y, to.y) - r - 36 : Math.max(from.y, to.y) + r + 36;
      const y1 = dashed ? from.y - r : from.y + r;
      const y2 = dashed ? to.y - r : to.y + r;
      d = `M ${sx(from.x)} ${sy(y1)} C ${sx(from.x)} ${sy(y)}, ${sx(to.x)} ${sy(y)}, ${sx(to.x)} ${sy(y2)}`;
      lx = sx((from.x + to.x) / 2);
      ly = sy(dashed ? y + 14 : y - 8);
    } else {
      const dx = to.x - from.x;
      const dy = to.y - from.y;
      const len = Math.hypot(dx, dy) || 1;
      const x1 = from.x + (dx / len) * r;
      const y1 = from.y + (dy / len) * r;
      const x2 = to.x - (dx / len) * r;
      const y2 = to.y - (dy / len) * r;
      const mid = (sx(x1) + sx(x2)) / 2;
      d = `M ${sx(x1)} ${sy(y1)} C ${mid} ${sy(y1)}, ${mid} ${sy(y2)}, ${sx(x2)} ${sy(y2)}`;
      lx = mid;
      ly = (sy(y1) + sy(y2)) / 2 - 8;
    }
    const label = typeof edge.label === "string" ? edge.label : "";
    return [
      `<path d="${d}" fill="none" stroke="#333" stroke-width="1.4" ${dashed ? 'stroke-dasharray="5 4"' : ""} marker-end="url(#arrow)"/>`,
      label
        ? `<text x="${lx}" y="${ly}" text-anchor="middle" font-family="Arial, sans-serif" font-size="11" fill="#333">${xml(label)}</text>`
        : "",
    ];
  });
  const circles = nodes.map((node) => {
    const data = node.data as StateNodeData;
    const center = centers.get(node.id)!;
    const x = sx(center.x);
    const y = sy(center.y);
    const lines = [data.label, data.caption, data.extra].filter(Boolean);
    const text = lines
      .map((line, index) => {
        const dy = (index - (lines.length - 1) / 2) * 14;
        const weight = index === 0 ? ' font-weight="700"' : "";
        const size = index === 0 ? 13 : 11;
        return `<text x="${x}" y="${y + dy + 4}" text-anchor="middle" font-family="Arial, sans-serif" font-size="${size}"${weight} fill="#222">${xml(line)}</text>`;
      })
      .join("");
    return `<circle cx="${x}" cy="${y}" r="${CIRCLE / 2 - 1}" fill="${data.initial ? "#f4f7fb" : "#fff"}" stroke="${data.current ? "#1565c0" : "#222"}" stroke-width="${data.current ? 3 : 1.6}" ${data.terminal ? 'stroke-dasharray="6 4"' : ""}/>${text}`;
  });
  return `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">
  <rect width="100%" height="100%" fill="#fff"/>
  <text x="24" y="28" font-family="Arial, sans-serif" font-size="16" font-weight="700" fill="#111">${xml(title)}</text>
  <defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 Z" fill="#333"/></marker></defs>
  <g>${paths.join("")}${circles.join("")}</g>
</svg>`;
}

function downloadBlob(filename: string, blob: Blob) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

function exportSvg(title: string, nodes: Node[], edges: Edge[]) {
  downloadBlob(`${fileSlug(title)}.svg`, new Blob([diagramSvg(title, nodes, edges)], { type: "image/svg+xml" }));
}

function exportPng(title: string, nodes: Node[], edges: Edge[]) {
  const svg = diagramSvg(title, nodes, edges);
  const image = new Image();
  const url = URL.createObjectURL(new Blob([svg], { type: "image/svg+xml" }));
  image.onload = () => {
    const canvas = document.createElement("canvas");
    const scale = 2;
    canvas.width = image.width * scale;
    canvas.height = image.height * scale;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.setTransform(scale, 0, 0, scale, 0, 0);
    ctx.drawImage(image, 0, 0);
    canvas.toBlob((blob) => {
      if (blob) downloadBlob(`${fileSlug(title)}.png`, blob);
      URL.revokeObjectURL(url);
    });
  };
  image.src = url;
}

function printDiagram(title: string, nodes: Node[], edges: Edge[]) {
  const frame = document.createElement("iframe");
  frame.setAttribute("title", title);
  frame.style.position = "fixed";
  frame.style.right = "0";
  frame.style.bottom = "0";
  frame.style.width = "0";
  frame.style.height = "0";
  frame.style.border = "0";
  document.body.appendChild(frame);
  const doc = frame.contentDocument;
  const view = frame.contentWindow;
  if (!doc || !view) {
    frame.remove();
    return;
  }
  doc.open();
  doc.write(`<!DOCTYPE html><html><head><title>${xml(title)}</title><style>
    @page { margin: 12mm; }
    body { margin: 0; }
    svg { width: 100%; height: auto; }
  </style></head><body>${diagramSvg(title, nodes, edges)}</body></html>`);
  doc.close();
  view.focus();
  view.print();
  window.setTimeout(() => frame.remove(), 1000);
}

function layoutPositions(states: PreviewState[], transitions: PreviewTransition[]) {
  const level = new Map<number, number>();
  const outgoing = new Map<number, PreviewTransition[]>();
  states.forEach((state) => outgoing.set(state.id, []));
  transitions.forEach((row) => {
    if (row.from_state_id && outgoing.has(row.from_state_id)) {
      outgoing.get(row.from_state_id)!.push(row);
    }
  });
  const starts = states.filter((state) => state.is_initial).map((state) => state.id);
  const roots = starts.length ? starts : states[0] ? [states[0].id] : [];
  roots.forEach((id) => level.set(id, 0));
  const queue = [...roots];
  while (queue.length) {
    const id = queue.shift()!;
    for (const row of outgoing.get(id) || []) {
      const next = row.to_state_id;
      if (!next || level.has(next)) continue;
      level.set(next, (level.get(id) || 0) + 1);
      queue.push(next);
    }
  }
  states.forEach((state) => {
    if (!level.has(state.id)) level.set(state.id, 0);
  });
  const columns = new Map<number, PreviewState[]>();
  states.forEach((state) => {
    const col = level.get(state.id) || 0;
    columns.set(col, [...(columns.get(col) || []), state]);
  });
  const pos = new Map<number, { x: number; y: number }>();
  columns.forEach((list, col) => {
    list.forEach((state, index) => {
      pos.set(state.id, { x: 48 + col * 300, y: 36 + index * 210 });
    });
  });
  return pos;
}

function readLayouts(): Record<string, Record<string, { x: number; y: number }>> {
  if (typeof window === "undefined") return {};
  try {
    return JSON.parse(localStorage.getItem(LAYOUT_KEY) || "{}");
  } catch {
    return {};
  }
}

function StateCircle({ data }: NodeProps) {
  const node = data as StateNodeData;
  const hidden = { opacity: 0, width: 8, height: 8 };
  return (
    <Box
      sx={{
        width: CIRCLE,
        height: CIRCLE,
        borderRadius: "50%",
        border: node.current ? "3px solid" : "2px solid",
        borderColor: node.current ? "primary.main" : "text.primary",
        borderStyle: node.terminal ? "dashed" : "solid",
        bgcolor: node.initial ? "action.selected" : "background.paper",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        textAlign: "center",
        px: 1.5,
        cursor: "grab",
      }}
    >
      <Handle id="in" type="target" position={Position.Left} style={hidden} />
      <Handle id="out" type="source" position={Position.Right} style={hidden} />
      <Handle id="back" type="source" position={Position.Bottom} style={hidden} />
      <Handle id="back-in" type="target" position={Position.Bottom} style={hidden} />
      <Handle id="up" type="source" position={Position.Top} style={hidden} />
      <Handle id="up-in" type="target" position={Position.Top} style={hidden} />
      <Box>
        <Typography variant="body2" fontWeight={700} sx={{ lineHeight: 1.2 }}>
          {node.label}
        </Typography>
        {node.caption ? (
          <Typography variant="caption" color="text.secondary" display="block">
            {node.caption}
          </Typography>
        ) : null}
        {node.extra ? (
          <Typography variant="caption" color="text.secondary" display="block">
            {node.extra}
          </Typography>
        ) : null}
      </Box>
    </Box>
  );
}

const nodeTypes = { state: StateCircle };

function WorkflowDiagram({
  title,
  states,
  transitions,
  currentStateId,
}: {
  title: string;
  states: PreviewState[];
  transitions: PreviewTransition[];
  currentStateId?: number;
}) {
  const theme = useTheme();
  const layoutId = states
    .map((state) => state.id)
    .sort((a, b) => a - b)
    .join("-");
  const signature = `${layoutId}:${currentStateId || 0}:${transitions.map((row) => row.id).join(",")}`;
  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const saved = readLayouts()[layoutId] || {};
    const pos = layoutPositions(states, transitions);
    setNodes(
      states.map((state) => {
        const id = String(state.id);
        return {
          id,
          type: "state",
          position: saved[id] || pos.get(state.id) || { x: 0, y: 0 },
          width: CIRCLE,
          height: CIRCLE,
          data: {
            label: state.name,
            caption: state.is_initial ? "Start" : state.is_terminal ? "End" : state.document_status || "",
            extra: state.escalation_hours ? `${state.escalation_hours}h` : "",
            current: state.id === currentStateId,
            terminal: Boolean(state.is_terminal),
            initial: Boolean(state.is_initial),
          },
          draggable: true,
          style: { width: CIRCLE, height: CIRCLE, background: "transparent", border: "none", padding: 0 },
        };
      })
    );
    const placed = new Map(
      states.map((state) => [state.id, saved[String(state.id)] || pos.get(state.id) || { x: 0, y: 0 }])
    );
    const nextEdges: Edge[] = transitions.flatMap((row) => {
      if (!row.from_state_id || !row.to_state_id) return [];
      const from = placed.get(row.from_state_id);
      const to = placed.get(row.to_state_id);
      const back = Boolean(from && to && to.x + 16 < from.x);
      return [
        {
          id: `t-${row.id}`,
          source: String(row.from_state_id),
          target: String(row.to_state_id),
          sourceHandle: back ? "back" : "out",
          targetHandle: back ? "back-in" : "in",
          label: edgeCaption(row),
          type: "smoothstep",
          markerEnd: { type: MarkerType.ArrowClosed, width: 16, height: 16 },
          style: { strokeWidth: 1.4 },
          labelStyle: { fontSize: 11, fill: theme.palette.text.primary },
          labelBgStyle: { fill: theme.palette.background.paper, fillOpacity: 0.92 },
          labelBgPadding: [4, 2],
        },
      ];
    });
    states.forEach((state) => {
      if (!state.escalate_to_id || state.escalate_to_id === state.id) return;
      nextEdges.push({
        id: `esc-${state.id}`,
        source: String(state.id),
        target: String(state.escalate_to_id),
        sourceHandle: "up",
        targetHandle: "up-in",
        label: "Escalate",
        type: "smoothstep",
        markerEnd: { type: MarkerType.ArrowClosed, width: 14, height: 14 },
        style: { strokeDasharray: "5 4", strokeWidth: 1.2 },
        labelStyle: { fontSize: 11, fill: theme.palette.text.primary },
        labelBgStyle: { fill: theme.palette.background.paper, fillOpacity: 0.92 },
        labelBgPadding: [4, 2],
      });
    });
    setEdges(nextEdges);
    setReady(true);
  }, [signature, layoutId, states, transitions, currentStateId, theme]);

  const onNodesChange = useCallback((changes: NodeChange[]) => {
    setNodes((current) => applyNodeChanges(changes, current));
  }, []);

  const onNodeDragStop = useCallback(
    (_event: unknown, node: Node) => {
      const all = readLayouts();
      const next = { ...(all[layoutId] || {}), [node.id]: node.position };
      all[layoutId] = next;
      localStorage.setItem(LAYOUT_KEY, JSON.stringify(all));
    },
    [layoutId]
  );

  const reset = () => {
    const all = readLayouts();
    delete all[layoutId];
    localStorage.setItem(LAYOUT_KEY, JSON.stringify(all));
    const pos = layoutPositions(states, transitions);
    setNodes((current) =>
      current.map((node) => ({
        ...node,
        position: pos.get(Number(node.id)) || node.position,
      }))
    );
  };

  const flowKey = useMemo(() => layoutId, [layoutId]);

  return (
    <Stack spacing={0.75}>
      <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap" alignItems="center" justifyContent="space-between">
        <Typography variant="caption" color="text.secondary">
          Drag a circle to arrange the diagram. A dashed arrow is an escalation. Export and print use this arrangement.
        </Typography>
        <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap">
          <Button size="small" onClick={() => exportSvg(title, nodes, edges)}>
            Export SVG
          </Button>
          <Button size="small" onClick={() => exportPng(title, nodes, edges)}>
            Export PNG
          </Button>
          <Button size="small" onClick={() => printDiagram(title, nodes, edges)}>
            Print
          </Button>
          <Button size="small" onClick={reset}>
            Reset layout
          </Button>
        </Stack>
      </Stack>
      <Box
        sx={{
          height: 460,
          border: 1,
          borderColor: "divider",
          borderRadius: 1,
          overflow: "hidden",
          bgcolor: "background.paper",
          "& .react-flow__node": { background: "transparent", border: "none", boxShadow: "none" },
        }}
      >
        {ready ? (
          <ReactFlow
            key={flowKey}
            nodes={nodes}
            edges={edges}
            nodeTypes={nodeTypes}
            onNodesChange={onNodesChange}
            onNodeDragStop={onNodeDragStop}
            fitView
            fitViewOptions={{ padding: 0.18 }}
            colorMode={theme.palette.mode}
            nodesConnectable={false}
            deleteKeyCode={null}
            minZoom={0.35}
            maxZoom={1.6}
          >
            <Background gap={18} />
            <Controls showInteractive={false} />
          </ReactFlow>
        ) : null}
      </Box>
    </Stack>
  );
}

export function WorkflowPreview({
  preview,
  currentStateId,
  title = "Workflow",
}: {
  preview?: WorkflowPreviewData | null;
  currentStateId?: number;
  title?: string;
}) {
  const states = preview?.states || [];
  const transitions = preview?.transitions || [];
  const triggers = preview?.triggers || [];
  if (!states.length) {
    return <Typography variant="body2">No states in this workflow yet.</Typography>;
  }
  return (
    <Stack spacing={1.5}>
      <WorkflowDiagram title={title} states={states} transitions={transitions} currentStateId={currentStateId} />
      {transitions.length ? (
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Action</TableCell>
              <TableCell>From</TableCell>
              <TableCell>To</TableCell>
              <TableCell>Rules</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {transitions.map((row) => (
              <TableRow key={row.id}>
                <TableCell>{row.label}</TableCell>
                <TableCell>{row.from_name}</TableCell>
                <TableCell>{row.to_name}</TableCell>
                <TableCell>
                  {row.require_signature ? "Signature · " : ""}
                  {row.require_comment ? "Comment · " : ""}
                  {row.block_self_approval ? "No self-approval · " : ""}
                  {(row.actions || []).map((action) => action.action_type).join(", ") || "—"}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      ) : null}
      {triggers.length ? (
        <Typography variant="body2">
          Triggers:{" "}
          {triggers
            .map(
              (trigger) =>
                `${trigger.event}${trigger.state_name ? ` (${trigger.state_name})` : ""} → ${(trigger.actions || []).map((action) => action.action_type).join(", ") || "none"}`
            )
            .join("; ")}
        </Typography>
      ) : null}
    </Stack>
  );
}

type Available = {
  id: number;
  label: string;
  to_state: string;
  require_comment?: boolean;
  require_signature?: boolean;
  block_self_approval?: boolean;
};
type HistoryRow = {
  id: number;
  kind: string;
  label: string;
  from_state: string;
  to_state: string;
  actor: string;
  comment: string;
  detail: string;
  at: string;
};
type SignatureRow = { id: number; signed_name: string; meaning: string; actor: string; signed_at: string };
export type DocumentWorkflow = {
  state_id?: number;
  state_name?: string;
  overdue?: boolean;
  escalated?: boolean;
  escalation_due_at?: string | null;
  transitions?: Available[];
  history?: HistoryRow[];
  signatures?: SignatureRow[];
  preview?: WorkflowPreviewData;
};

export function DocumentWorkflowPanel({
  id,
  workflow,
  onDone,
}: {
  id: string;
  workflow: DocumentWorkflow | null;
  onDone: () => void;
}) {
  const { run, busy } = useRecordAction();
  const [pending, setPending] = useState<Available | null>(null);
  const [comment, setComment] = useState("");
  const [signedName, setSignedName] = useState("");
  const [meaning, setMeaning] = useState("approve");

  const act = async (transition: Available, extra?: { comment?: string; signed_name?: string; meaning?: string }) => {
    const res = await run(`tr-${transition.id}`, `/dms/documents/${id}/transition/`, {
      body: { transition: transition.id, ...extra },
      success: transition.label,
    });
    if (res) {
      setPending(null);
      setComment("");
      setSignedName("");
      onDone();
    }
  };

  if (!workflow) {
    return (
      <Paper variant="outlined" sx={{ p: 2, mt: 2 }}>
        <Typography variant="subtitle1" sx={{ mb: 1 }}>
          Workflow
        </Typography>
        <Button
          variant="contained"
          disabled={busy}
          onClick={() =>
            void run(`start-${id}`, `/dms/documents/${id}/start-workflow/`, {
              success: "Workflow started",
            }).then((res) => {
              if (res) onDone();
            })
          }
        >
          Start document workflow
        </Button>
      </Paper>
    );
  }

  return (
    <Paper variant="outlined" sx={{ p: 2, mt: 2 }}>
      <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
        <Typography variant="subtitle1">Workflow</Typography>
        <Chip size="small" label={workflow.state_name || "State"} color="primary" />
        {workflow.escalated ? <Chip size="small" label="Escalated" color="warning" /> : null}
      </Stack>
      <WorkflowPreview preview={workflow.preview} currentStateId={workflow.state_id} title="Document workflow" />
      {workflow.escalation_due_at ? (
        <Typography variant="body2" sx={{ mt: 1 }}>
          Escalation due {formatDate(workflow.escalation_due_at)}
        </Typography>
      ) : null}
      <Stack direction="row" spacing={1} sx={{ mt: 1.5, flexWrap: "wrap" }} useFlexGap>
        {(workflow.transitions || []).map((transition) => (
          <Button
            key={transition.id}
            variant="contained"
            disabled={busy}
            onClick={() => {
              if (transition.require_comment || transition.require_signature) {
                setPending(transition);
                return;
              }
              void act(transition);
            }}
          >
            {transition.label}
          </Button>
        ))}
        {workflow.overdue ? (
          <Button
            variant="outlined"
            color="warning"
            disabled={busy}
            onClick={() =>
              void run(`esc-${id}`, `/dms/documents/${id}/escalate/`, {
                success: "Escalated",
              }).then((res) => {
                if (res) onDone();
              })
            }
          >
            Escalate
          </Button>
        ) : null}
      </Stack>
      {(workflow.signatures || []).length ? (
        <Typography variant="body2" sx={{ mt: 1.5 }}>
          Signatures:{" "}
          {(workflow.signatures || [])
            .map((row) => `${row.signed_name} (${row.meaning})`)
            .join(", ")}
        </Typography>
      ) : null}
      {(workflow.history || []).length ? (
        <Stack spacing={0.5} sx={{ mt: 1.5 }}>
          {(workflow.history || []).map((row) => (
            <Typography key={row.id} variant="body2">
              {formatDate(row.at)} · {row.actor || "System"} · {row.label}
              {row.to_state ? ` → ${row.to_state}` : ""}
              {row.comment ? ` — ${row.comment}` : ""}
            </Typography>
          ))}
        </Stack>
      ) : null}
      <Dialog open={!!pending} onClose={() => setPending(null)} fullWidth maxWidth="xs">
        <DialogTitle>{pending?.label}</DialogTitle>
        <DialogContent>
          <Stack
            component="form"
            spacing={1.5}
            sx={{ mt: 1 }}
            onSubmit={(e: FormEvent) => {
              e.preventDefault();
              if (!pending) return;
              void act(pending, { comment, signed_name: signedName, meaning });
            }}
          >
            {pending?.require_comment ? (
              <TextField
                label="Comment"
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                required
                fullWidth
              />
            ) : null}
            {pending?.require_signature ? (
              <>
                <TextField
                  label="Sign with your name"
                  value={signedName}
                  onChange={(e) => setSignedName(e.target.value)}
                  required
                  fullWidth
                />
                <TextField
                  select
                  label="Meaning"
                  value={meaning}
                  onChange={(e) => setMeaning(e.target.value)}
                  fullWidth
                >
                  <MenuItem value="approve">Approve</MenuItem>
                  <MenuItem value="review">Review</MenuItem>
                  <MenuItem value="acknowledge">Acknowledge</MenuItem>
                </TextField>
              </>
            ) : null}
            <DialogActions sx={{ px: 0 }}>
              <Button onClick={() => setPending(null)}>Cancel</Button>
              <Button type="submit" variant="contained" disabled={busy}>
                Confirm
              </Button>
            </DialogActions>
          </Stack>
        </DialogContent>
      </Dialog>
    </Paper>
  );
}
