const ORDER = { critical: 0, warning: 1, info: 2 };

export default function IssuesPanel({ issues, activeNode }) {
  const sorted = [...issues].sort((a, b) => (ORDER[a.severity] ?? 3) - (ORDER[b.severity] ?? 3));
  const visible = activeNode
  ? sorted.filter(i =>
      i.affected_nodes?.some(n =>
        n.toLowerCase().includes(activeNode.toLowerCase()) ||
        activeNode.toLowerCase().includes(n.toLowerCase())
      )
    )
  : sorted;

  return (
    <div className="issues-panel">
      <p className="panel-label">
        // Issues{" "}
        <span style={{ color: "var(--text-3)", fontWeight: 400 }}>
          ({visible.length}){activeNode && ` · ${activeNode}`}
        </span>
      </p>

      {visible.length === 0 && (
        <p className="no-issues">✓ No issues{activeNode ? " for this module" : ""}.</p>
      )}

      {visible.map((issue, idx) => (
        <div key={idx} className={`issue-item ${activeNode ? "highlighted" : ""}`}>
          <div className="issue-header">
            <span className={`severity-badge sev-${issue.severity}`}>{issue.severity}</span>
            <span className="issue-title">{issue.title}</span>
          </div>
          <p className="issue-desc">{issue.description}</p>
          <p className="issue-fix">→ {issue.suggestion}</p>
          {issue.affected_nodes?.length > 0 && (
            <div className="issue-nodes">
              {issue.affected_nodes.map(n => <span key={n} className="issue-node-tag">{n}</span>)}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}