import { useCallback, useMemo } from "react";
import ReactFlow, {
  Background, Controls, MiniMap,
  useNodesState, useEdgesState,
  Position, MarkerType,
} from "reactflow";
import "reactflow/dist/style.css";

const TYPE_COLORS = {
  module:  "#5af0a0",
  service: "#60a8f0",
  utility: "#a080f0",
  model:   "#f0c040",
  router:  "#f08060",
  config:  "#808080",
  test:    "#555",
};

function CustomNode({ data, selected }) {
  const hasCritical = data.issues.some(i => i.includes("Circular"));
  const hasIssues   = data.issues.length > 0;
  const cls = [
    "custom-node",
    selected ? "selected" : "",
    hasCritical ? "has-critical" : hasIssues ? "has-issues" : "",
  ].join(" ");

  return (
    <div className={cls} title={data.issues.join("\n") || "No issues"}>
      <div style={{ display: "flex", alignItems: "center", marginBottom: 3 }}>
        <span className="node-type-dot" style={{ background: TYPE_COLORS[data.nodeType] || "#666" }} />
        <span className="node-label">{data.label}</span>
      </div>
      <div className="node-meta">{data.fileCount} files · {(data.lines || 0).toLocaleString()} lines</div>
      {data.issues.length > 0 && (
        <div className="node-issues-count">⚠ {data.issues.length} issue{data.issues.length > 1 ? "s" : ""}</div>
      )}
    </div>
  );
}

const nodeTypes = { custom: CustomNode };

function layoutNodes(nodes, edges) {
  const inDegree = {};
  nodes.forEach(n => (inDegree[n.id] = 0));
  edges.forEach(e => { if (e.target in inDegree) inDegree[e.target]++; });

  const tiers = {};
  nodes.forEach(n => {
    const tier = Math.min(inDegree[n.id], 4);
    if (!tiers[tier]) tiers[tier] = [];
    tiers[tier].push(n.id);
  });

  const positions = {};
  Object.keys(tiers).sort((a, b) => a - b).forEach((tier, tierIdx) => {
    const ids = tiers[tier];
    const totalWidth = (ids.length - 1) * 170;
    ids.forEach((id, i) => {
      positions[id] = { x: i * 170 - totalWidth / 2 + 300, y: tierIdx * 160 + 20 };
    });
  });
  return positions;
}

export default function GraphCanvas({ nodes: rawNodes, edges: rawEdges, onNodeClick, activeNode }) {
  const positions = useMemo(() => layoutNodes(rawNodes, rawEdges), [rawNodes, rawEdges]);

  const initialNodes = useMemo(() =>
    rawNodes.map(n => ({
      id: n.id,
      type: "custom",
      position: positions[n.id] || { x: 0, y: 0 },
      sourcePosition: Position.Bottom,
      targetPosition: Position.Top,
      data: {
        label: n.label, nodeType: n.type,
        fileCount: n.file_count, lines: n.metrics?.lines, issues: n.issues,
      },
      selected: n.id === activeNode,
    })),
  [rawNodes, positions, activeNode]);

  const initialEdges = useMemo(() =>
    rawEdges.map((e, idx) => ({
      id: `e-${idx}`,
      source: e.source,
      target: e.target,
      label: e.weight > 1 ? `${e.weight}` : "",
      labelStyle: { fill: "#555", fontSize: 9, fontFamily: "IBM Plex Mono" },
      style: {
        stroke: e.weight > 3 ? "rgba(240,192,64,0.5)" : "rgba(255,255,255,0.12)",
        strokeWidth: Math.min(e.weight, 4),
      },
      markerEnd: { type: MarkerType.ArrowClosed, color: "rgba(255,255,255,0.2)" },
    })),
  [rawEdges]);

  const [nodes, , onNodesChange] = useNodesState(initialNodes);
  const [edges, , onEdgesChange] = useEdgesState(initialEdges);

  const handleNodeClick = useCallback((_, node) => {
    onNodeClick(node.id === activeNode ? null : node.id);
  }, [onNodeClick, activeNode]);

  return (
    <div className="graph-container">
      <ReactFlow
        nodes={nodes} edges={edges}
        onNodesChange={onNodesChange} onEdgesChange={onEdgesChange}
        onNodeClick={handleNodeClick}
        proOptions={{ hideAttribution: true }}
        nodeTypes={nodeTypes}
        fitView fitViewOptions={{ padding: 0.4 }}
        minZoom={0.3} maxZoom={2}
        style={{ background: "transparent" }}
      >
        <Background color="rgba(255,255,255,0.03)" gap={24} size={1} />
        <Controls style={{ background: "var(--bg-3)", border: "1px solid var(--border)", borderRadius: 6 }} />
        <MiniMap
          nodeColor={n => TYPE_COLORS[n.data?.nodeType] || "#333"}
          maskColor="rgba(10,10,11,0.8)"
          style={{ background: "var(--bg-2)", border: "1px solid var(--border)" }}
        />
      </ReactFlow>

      <div className="graph-legend">
        {Object.entries(TYPE_COLORS).map(([type, color]) => (
          <div key={type} className="legend-item">
            <span style={{ width: 8, height: 8, borderRadius: "50%", background: color, display: "inline-block" }} />
            {type}
          </div>
        ))}
      </div>

      {activeNode && (
        <div style={{
          position: "absolute", top: 12, left: "50%", transform: "translateX(-50%)",
          background: "var(--bg-2)", border: "1px solid var(--accent)",
          borderRadius: 4, padding: "5px 14px",
          fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--accent)",
        }}>
          {activeNode} selected · click again to deselect
        </div>
      )}
    </div>
  );
}