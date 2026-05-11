import { useState, useEffect } from "react";

export default function AnalysisForm({ onAnalyze }) {
  const [models, setModels] = useState(["llama3"]); // fallback default
  const [loadingModels, setLoadingModels] = useState(true);
  const [repoUrl, setRepoUrl]         = useState("");
  const [githubToken, setGithubToken] = useState("");
  const [ollamaModel, setOllamaModel] = useState("llama3");
  const [showToken, setShowToken]     = useState(false);

  useEffect(() => {
    fetch("http://localhost:11434/api/tags")
      .then(r => r.json())
      .then(data => {
        const names = data.models?.map(m => m.name) ?? [];
        if (names.length > 0) {
          setModels(names);
          setOllamaModel(names[0]);
        }
      })
      .catch(() => {
        // Ollama not reachable — keep the fallback default
      })
      .finally(() => setLoadingModels(false));
  }, []);

  const isValid = repoUrl.includes("github.com/");

  return (
    <div className="form-card">
      <p className="form-title">// Analyze Repository</p>

      <div className="field">
        <label>GitHub Repository URL</label>
        <input
          type="url"
          placeholder="https://github.com/owner/repo"
          value={repoUrl}
          onChange={(e) => setRepoUrl(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && isValid && onAnalyze({ repoUrl, githubToken, ollamaModel })}
        />
      </div>

      <div className="field">
        <label>
          Ollama Model{" "}
          {loadingModels && (
            <span style={{ color: "var(--text-3)", fontWeight: 400 }}>(detecting...)</span>
          )}
        </label>
        <select
          value={ollamaModel}
          onChange={(e) => setOllamaModel(e.target.value)}
          disabled={loadingModels}
        >
          {models.map((m) => <option key={m} value={m}>{m}</option>)}
        </select>
      </div>

      <div className="field">
        <label>
          GitHub Token{" "}
          <span style={{ color: "var(--text-3)", fontWeight: 400 }}>(optional — private repos)</span>
        </label>
        <input
          type={showToken ? "text" : "password"}
          placeholder="ghp_xxxxxxxxxxxx"
          value={githubToken}
          onChange={(e) => setGithubToken(e.target.value)}
        />
        <span
          style={{ fontSize: 10, color: "var(--text-3)", cursor: "pointer", fontFamily: "var(--font-mono)" }}
          onClick={() => setShowToken((v) => !v)}
        >
          {showToken ? "hide" : "show"}
        </span>
      </div>

      <button
        className="btn-primary"
        onClick={() => onAnalyze({ repoUrl, githubToken, ollamaModel })}
        disabled={!isValid}
      >
        RUN ANALYSIS →
      </button>
    </div>
  );
}