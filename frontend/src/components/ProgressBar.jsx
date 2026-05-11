export default function ProgressBar({ step, message }) {
  return (
    <div className="progress-wrap">
      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <div className="progress-spinner" />
        <span className="progress-label">Analyzing repository...</span>
      </div>
      <div className="progress-steps">
        {Array.from({ length: 6 }).map((_, i) => (
          <div
            key={i}
            className={`progress-dot ${i < step - 1 ? "done" : i === step - 1 ? "active" : ""}`}
          />
        ))}
      </div>
      <p className="progress-message">→ {message}</p>
    </div>
  );
}