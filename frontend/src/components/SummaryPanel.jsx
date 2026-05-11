export default function SummaryPanel({ result, onReset }) {
  const m = result.metrics || {};
  return (
    <div className="summary-panel">
      <p className="panel-label">// Overview</p>
      <p className="summary-repo">{result.repo_name}</p>

      <div className="metric-grid">
        <div className="metric-box">
          <div className="metric-val">{result.nodes.length}</div>
          <div className="metric-key">modules</div>
        </div>
        <div className="metric-box">
          <div className="metric-val">{result.edges.length}</div>
          <div className="metric-key">dependencies</div>
        </div>
        <div className="metric-box">
          <div className="metric-val" style={{ color: "var(--danger)" }}>
            {result.issues.filter(i => i.severity === "critical").length}
          </div>
          <div className="metric-key">critical</div>
        </div>
        <div className="metric-box">
          <div className="metric-val">{m.code_files || "—"}</div>
          <div className="metric-key">files read</div>
        </div>
      </div>

      {result.tech_stack?.length > 0 && (
        <>
          <p className="panel-label" style={{ marginBottom: 8 }}>// Tech Stack</p>
          <div className="tag-list">
            {result.tech_stack.map((t) => <span key={t} className="tag">{t}</span>)}
          </div>
        </>
      )}

      {m.architectural_pattern && (
        <div className="tag-list">
          <span className="tag" style={{ color: "var(--accent)", borderColor: "rgba(90,240,160,0.25)" }}>
            {m.architectural_pattern}
          </span>
          {m.project_type && (
            <span className="tag" style={{ color: "var(--info)", borderColor: "rgba(96,168,240,0.25)" }}>
              {m.project_type}
            </span>
          )}
        </div>
      )}

      <p className="panel-label" style={{ marginBottom: 8, marginTop: 14 }}>// AI Summary</p>
      <p className="summary-text">{result.summary}</p>
      <button className="btn-secondary" onClick={onReset}>← New Analysis</button>
    </div>
  );
}