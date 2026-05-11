import { useState } from "react";
import AnalysisForm from "./components/AnalysisForm";
import GraphCanvas from "./components/GraphCanvas";
import IssuesPanel from "./components/IssuesPanel";
import SummaryPanel from "./components/SummaryPanel";
import ProgressBar from "./components/ProgressBar";
import "./index.css";

export default function App() {
  const [phase, setPhase] = useState("idle");
  const [progress, setProgress] = useState({ step: 0, message: "" });
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [activeNode, setActiveNode] = useState(null);

  const handleAnalyze = async ({ repoUrl, githubToken, ollamaModel }) => {
    setPhase("loading");
    setResult(null);
    setError("");
    setActiveNode(null);

    try {
      const res = await fetch("http://localhost:8000/api/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          repo_url: repoUrl,
          github_token: githubToken || undefined,
          ollama_model: ollamaModel,
        }),
      });

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n\n");
        buffer = lines.pop() || "";

        for (const block of lines) {
          const eventMatch = block.match(/^event: (\w+)/m);
          const dataMatch  = block.match(/^data: (.+)$/m);
          if (!eventMatch || !dataMatch) continue;
          const event = eventMatch[1];
          const data  = JSON.parse(dataMatch[1]);

          if (event === "progress")     { setProgress(data); }
          else if (event === "result")  { setResult(data); setPhase("done"); }
          else if (event === "error")   { setError(data.message); setPhase("error"); }
        }
      }
    } catch {
      setError("Connection failed. Is the backend running?");
      setPhase("error");
    }
  };

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-left">
          <span className="logo-mark">⬡</span>
          <span className="logo-text">ARCHREVIEW</span>
          <span className="logo-sub">/ AI Code Architecture Analyzer</span>
        </div>
        {result && (
          <div className="repo-badge">
            <span className="repo-badge-dot" />
            {result.repo_name}
          </div>
        )}
      </header>

      <main className="app-main">
        {phase === "idle" && (
          <div className="landing">
            <div className="landing-hero">
              <h1 className="hero-title">
                Understand any<br />
                <em>GitHub repository</em><br />
                in seconds.
              </h1>
              <p className="hero-sub">
                Multi-agent AI analyzes dependencies, detects anti-patterns,
                and maps your architecture — fully local with Ollama.
              </p>
            </div>
            <AnalysisForm onAnalyze={handleAnalyze} />
          </div>
        )}

        {phase === "loading" && (
          <div className="loading-screen">
            <ProgressBar step={progress.step} message={progress.message} />
          </div>
        )}

        {phase === "error" && (
          <div className="error-screen">
            <div className="error-box">
              <span className="error-icon">✕</span>
              <p className="error-msg">{error}</p>
              <button className="btn-secondary" onClick={() => setPhase("idle")}>
                Try Again
              </button>
            </div>
          </div>
        )}

        {phase === "done" && result && (
          <div className="results-layout">
            <div className="results-left">
              <SummaryPanel result={result} onReset={() => setPhase("idle")} />
              <IssuesPanel issues={result.issues} activeNode={activeNode} />
            </div>
            <div className="results-graph">
              <GraphCanvas
                nodes={result.nodes}
                edges={result.edges}
                onNodeClick={setActiveNode}
                activeNode={activeNode}
              />
            </div>
          </div>
        )}
      </main>
    </div>
  );
}