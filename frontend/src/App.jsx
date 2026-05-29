import { useState, useRef } from "react";

const API = "";

const hackerStyles = `
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Syne:wght@400;600;800&display=swap');
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  :root {
    --bg: #0a0a0f; --surface: #111118; --border: #1e1e2e;
    --accent: #00ff9d; --accent2: #7c6aff; --text: #e8e8f0; --muted: #555570;
    --error: #ff4d6d; --mono: 'JetBrains Mono', monospace; --sans: 'Syne', sans-serif;
  }
  body { background: var(--bg); color: var(--text); font-family: var(--sans); min-height: 100vh; }
  .app { max-width: 900px; margin: 0 auto; padding: 2rem 1.5rem; }
  .header { display: flex; align-items: flex-end; justify-content: space-between; margin-bottom: 2.5rem; padding-bottom: 1.5rem; border-bottom: 1px solid var(--border); }
  .logo { display: flex; flex-direction: column; gap: 0.2rem; }
  .logo-title { font-size: 1.6rem; font-weight: 800; letter-spacing: -0.03em; background: linear-gradient(90deg, var(--accent), var(--accent2)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
  .logo-sub { font-family: var(--mono); font-size: 0.7rem; color: var(--muted); letter-spacing: 0.1em; }
  .header-right { display: flex; align-items: center; gap: 0.75rem; }
  .session-badge { font-family: var(--mono); font-size: 0.65rem; color: var(--accent); background: rgba(0,255,157,0.08); border: 1px solid rgba(0,255,157,0.2); padding: 0.4rem 0.8rem; border-radius: 4px; max-width: 220px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .theme-toggle { font-family: var(--mono); font-size: 0.65rem; padding: 0.4rem 0.8rem; border-radius: 4px; border: 1px solid var(--border); background: transparent; color: var(--muted); cursor: pointer; transition: all 0.15s; white-space: nowrap; }
  .theme-toggle:hover { border-color: var(--accent2); color: var(--accent2); }
  .upload-zone { border: 1.5px dashed var(--border); border-radius: 8px; padding: 2.5rem; text-align: center; cursor: pointer; transition: border-color 0.2s, background 0.2s; background: var(--surface); margin-bottom: 1rem; }
  .upload-zone:hover, .upload-zone.drag { border-color: var(--accent); background: rgba(0,255,157,0.03); }
  .upload-zone input { display: none; }
  .upload-icon { font-size: 2rem; margin-bottom: 0.75rem; }
  .upload-title { font-weight: 600; font-size: 1rem; margin-bottom: 0.4rem; }
  .upload-hint { font-family: var(--mono); font-size: 0.7rem; color: var(--muted); }
  .btn { font-family: var(--mono); font-size: 0.8rem; font-weight: 600; padding: 0.65rem 1.4rem; border-radius: 5px; border: none; cursor: pointer; transition: all 0.15s; letter-spacing: 0.05em; }
  .btn-primary { background: var(--accent); color: #000; }
  .btn-primary:hover { background: #00e68a; }
  .btn-primary:disabled { opacity: 0.4; cursor: not-allowed; }
  .btn-ghost { background: transparent; color: var(--muted); border: 1px solid var(--border); }
  .btn-ghost:hover { border-color: var(--accent2); color: var(--accent2); }
  .btn-danger { background: transparent; color: var(--error); border: 1px solid var(--error); }
  .btn-danger:hover { background: rgba(255,77,109,0.1); }
  .tabs { display: flex; gap: 0.25rem; margin-bottom: 1.5rem; border-bottom: 1px solid var(--border); }
  .tab { font-family: var(--mono); font-size: 0.75rem; padding: 0.6rem 1.2rem; cursor: pointer; color: var(--muted); border-bottom: 2px solid transparent; transition: all 0.15s; background: none; border-top: none; border-left: none; border-right: none; letter-spacing: 0.05em; }
  .tab:hover { color: var(--text); }
  .tab.active { color: var(--accent); border-bottom-color: var(--accent); }
  .input-row { display: flex; gap: 0.5rem; margin-bottom: 1.5rem; }
  .input { flex: 1; background: var(--surface); border: 1px solid var(--border); border-radius: 5px; padding: 0.65rem 1rem; color: var(--text); font-family: var(--mono); font-size: 0.82rem; outline: none; transition: border-color 0.15s; }
  .input:focus { border-color: var(--accent2); }
  .answer-box { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 1.25rem; margin-bottom: 1rem; font-size: 0.88rem; line-height: 1.7; white-space: pre-wrap; }
  .answer-label { font-family: var(--mono); font-size: 0.65rem; color: var(--accent); letter-spacing: 0.1em; margin-bottom: 0.5rem; }
  .sources { display: flex; flex-direction: column; gap: 0.5rem; }
  .source-chip { display: flex; justify-content: space-between; align-items: center; background: var(--surface); border: 1px solid var(--border); border-radius: 5px; padding: 0.6rem 1rem; font-family: var(--mono); font-size: 0.72rem; }
  .source-file { color: var(--accent2); } .source-name { color: var(--text); } .source-score { color: var(--accent); }
  .result-card { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 1rem 1.25rem; margin-bottom: 0.75rem; }
  .result-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem; }
  .result-name { font-weight: 600; font-size: 0.9rem; }
  .result-meta { font-family: var(--mono); font-size: 0.65rem; color: var(--muted); margin-bottom: 0.6rem; }
  .code-block { background: #0d0d14; border-radius: 5px; padding: 0.8rem; font-family: var(--mono); font-size: 0.72rem; color: #a8a8c0; overflow-x: auto; max-height: 180px; overflow-y: auto; white-space: pre; }
  .summary-box { background: var(--surface); border: 1px solid var(--border); border-left: 3px solid var(--accent2); border-radius: 8px; padding: 1.5rem; font-size: 0.88rem; line-height: 1.8; white-space: pre-wrap; }
  .status { font-family: var(--mono); font-size: 0.75rem; color: var(--muted); margin-bottom: 1rem; }
  .status.loading { color: var(--accent2); } .status.error { color: var(--error); } .status.success { color: var(--accent); }
  .stats-row { display: flex; gap: 1rem; margin-bottom: 1.5rem; flex-wrap: wrap; }
  .stat { background: var(--surface); border: 1px solid var(--border); border-radius: 6px; padding: 0.75rem 1.25rem; font-family: var(--mono); font-size: 0.7rem; }
  .stat-val { font-size: 1.3rem; font-weight: 700; color: var(--accent); font-family: var(--sans); }
  .stat-label { color: var(--muted); margin-top: 0.2rem; }
  .section-title { font-family: var(--mono); font-size: 0.65rem; color: var(--muted); letter-spacing: 0.12em; margin-bottom: 0.75rem; }
  .divider { height: 1px; background: var(--border); margin: 1.5rem 0; }
  .empty { text-align: center; color: var(--muted); font-family: var(--mono); font-size: 0.8rem; padding: 3rem 0; }
`;

const saasStyles = `
  @import url('https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=DM+Sans:wght@300;400;500;600&display=swap');
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  :root {
    --bg: #f9f9f7; --surface: #ffffff; --border: #e8e6e0; --border2: #d4d0c8;
    --accent: #1a1a1a; --accent2: #2563eb; --text: #1a1a1a; --muted: #888880;
    --error: #dc2626; --success: #16a34a;
    --mono: 'DM Mono', monospace; --sans: 'DM Sans', sans-serif; --serif: 'Instrument Serif', serif;
    --shadow: 0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04);
    --shadow-md: 0 4px 12px rgba(0,0,0,0.08), 0 2px 4px rgba(0,0,0,0.04);
  }
  body { background: var(--bg); color: var(--text); font-family: var(--sans); min-height: 100vh; }
  .app { max-width: 860px; margin: 0 auto; padding: 3rem 2rem; }
  .header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 3rem; }
  .logo { display: flex; flex-direction: column; gap: 0.15rem; }
  .logo-title { font-family: var(--serif); font-size: 1.75rem; font-weight: 400; font-style: italic; letter-spacing: -0.01em; color: var(--text); }
  .logo-sub { font-size: 0.72rem; color: var(--muted); font-weight: 400; letter-spacing: 0.02em; }
  .header-right { display: flex; align-items: center; gap: 0.75rem; }
  .session-badge { font-size: 0.72rem; color: var(--accent2); background: #eff6ff; border: 1px solid #bfdbfe; padding: 0.35rem 0.75rem; border-radius: 20px; max-width: 220px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .theme-toggle { font-size: 0.72rem; padding: 0.4rem 0.85rem; border-radius: 20px; border: 1px solid var(--border2); background: var(--surface); color: var(--muted); cursor: pointer; transition: all 0.15s; white-space: nowrap; box-shadow: var(--shadow); }
  .theme-toggle:hover { border-color: var(--accent); color: var(--text); }
  .upload-zone { border: 1.5px dashed var(--border2); border-radius: 12px; padding: 3rem 2rem; text-align: center; cursor: pointer; transition: all 0.2s; background: var(--surface); margin-bottom: 1rem; box-shadow: var(--shadow); }
  .upload-zone:hover, .upload-zone.drag { border-color: var(--accent2); background: #f8fbff; box-shadow: var(--shadow-md); }
  .upload-zone input { display: none; }
  .upload-icon { font-size: 1.75rem; margin-bottom: 0.75rem; opacity: 0.6; }
  .upload-title { font-weight: 500; font-size: 0.95rem; margin-bottom: 0.35rem; color: var(--text); }
  .upload-hint { font-size: 0.75rem; color: var(--muted); }
  .btn { font-family: var(--sans); font-size: 0.82rem; font-weight: 500; padding: 0.6rem 1.25rem; border-radius: 8px; border: none; cursor: pointer; transition: all 0.15s; }
  .btn-primary { background: var(--accent); color: #fff; box-shadow: var(--shadow); }
  .btn-primary:hover { background: #333; box-shadow: var(--shadow-md); }
  .btn-primary:disabled { opacity: 0.4; cursor: not-allowed; }
  .btn-ghost { background: var(--surface); color: var(--muted); border: 1px solid var(--border2); box-shadow: var(--shadow); }
  .btn-ghost:hover { color: var(--text); border-color: var(--accent); }
  .btn-danger { background: var(--surface); color: var(--error); border: 1px solid #fecaca; box-shadow: var(--shadow); }
  .btn-danger:hover { background: #fef2f2; }
  .tabs { display: flex; gap: 0; margin-bottom: 2rem; border-bottom: 1px solid var(--border); }
  .tab { font-size: 0.82rem; font-weight: 400; padding: 0.65rem 1.25rem; cursor: pointer; color: var(--muted); border-bottom: 2px solid transparent; transition: all 0.15s; background: none; border-top: none; border-left: none; border-right: none; }
  .tab:hover { color: var(--text); }
  .tab.active { color: var(--text); border-bottom-color: var(--text); font-weight: 500; }
  .input-row { display: flex; gap: 0.5rem; margin-bottom: 1.5rem; }
  .input { flex: 1; background: var(--surface); border: 1px solid var(--border2); border-radius: 8px; padding: 0.7rem 1rem; color: var(--text); font-family: var(--sans); font-size: 0.88rem; outline: none; transition: border-color 0.15s; box-shadow: var(--shadow); }
  .input:focus { border-color: var(--accent2); box-shadow: 0 0 0 3px rgba(37,99,235,0.08); }
  .answer-box { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 1.5rem; margin-bottom: 1rem; font-size: 0.88rem; line-height: 1.8; white-space: pre-wrap; box-shadow: var(--shadow); color: var(--text); }
  .answer-label { font-size: 0.68rem; font-weight: 600; color: var(--muted); letter-spacing: 0.1em; text-transform: uppercase; margin-bottom: 0.6rem; }
  .sources { display: flex; flex-direction: column; gap: 0.4rem; }
  .source-chip { display: flex; justify-content: space-between; align-items: center; background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 0.6rem 1rem; font-size: 0.75rem; box-shadow: var(--shadow); }
  .source-file { color: var(--accent2); font-weight: 500; } .source-name { color: var(--text); } .source-score { color: var(--success); font-weight: 500; }
  .result-card { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 1.25rem; margin-bottom: 0.75rem; box-shadow: var(--shadow); transition: box-shadow 0.15s; }
  .result-card:hover { box-shadow: var(--shadow-md); }
  .result-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.4rem; }
  .result-name { font-weight: 600; font-size: 0.9rem; }
  .result-meta { font-size: 0.72rem; color: var(--muted); margin-bottom: 0.75rem; }
  .code-block { background: #f6f5f2; border-radius: 8px; padding: 1rem; font-family: 'DM Mono', monospace; font-size: 0.72rem; color: #555; overflow-x: auto; max-height: 180px; overflow-y: auto; white-space: pre; border: 1px solid var(--border); }
  .summary-box { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 1.75rem; font-size: 0.9rem; line-height: 1.85; white-space: pre-wrap; box-shadow: var(--shadow); }
  .status { font-size: 0.78rem; color: var(--muted); margin-bottom: 1rem; }
  .status.loading { color: var(--accent2); } .status.error { color: var(--error); } .status.success { color: var(--success); }
  .stats-row { display: flex; gap: 0.75rem; margin-bottom: 2rem; flex-wrap: wrap; }
  .stat { background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 1rem 1.5rem; font-size: 0.72rem; box-shadow: var(--shadow); flex: 1; min-width: 100px; }
  .stat-val { font-family: var(--serif); font-size: 1.6rem; font-weight: 400; font-style: italic; color: var(--text); }
  .stat-label { color: var(--muted); margin-top: 0.15rem; font-size: 0.7rem; }
  .section-title { font-size: 0.68rem; font-weight: 600; color: var(--muted); letter-spacing: 0.1em; text-transform: uppercase; margin-bottom: 0.75rem; }
  .divider { height: 1px; background: var(--border); margin: 1.5rem 0; }
  .empty { text-align: center; color: var(--muted); font-size: 0.85rem; padding: 4rem 0; line-height: 1.6; }
`;

export default function App() {
  const [theme, setTheme] = useState("saas");
  const [session, setSession] = useState(null);
  const [tab, setTab] = useState("ask");
  const [uploading, setUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState("");
  const [drag, setDrag] = useState(false);
  const fileRef = useRef();

  const [query, setQuery] = useState("");
  const [asking, setAsking] = useState(false);
  const [answer, setAnswer] = useState(null);

  const [searchQ, setSearchQ] = useState("");
  const [searching, setSearching] = useState(false);
  const [searchResults, setSearchResults] = useState(null);

  const [summary, setSummary] = useState(null);
  const [summarizing, setSummarizing] = useState(false);

  const [githubUrl, setGithubUrl] = useState("");
  const [indexing, setIndexing] = useState(false);

  async function handleUpload(file) {
    if (!file || !file.name.endsWith(".zip")) { setUploadStatus("error:Only .zip files supported"); return; }
    setUploading(true); setUploadStatus("loading:Uploading and indexing...");
    const fd = new FormData(); fd.append("file", file);
    try {
      const res = await fetch(`${API}/repo/upload`, { method: "POST", body: fd });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Upload failed");
      setSession(data); setUploadStatus("success:Indexed successfully!");
      setSummary(null); setAnswer(null); setSearchResults(null);
    } catch (e) { setUploadStatus(`error:${e.message}`); }
    finally { setUploading(false); }
  }

  async function handleIndexUrl() {
    if (!githubUrl.trim()) return;
    setIndexing(true); setUploadStatus("loading:Cloning and indexing...");
    try {
      const res = await fetch(`${API}/repo/index-url`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: githubUrl })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed");
      setSession(data); setUploadStatus("success:Indexed successfully!");
      setSummary(null); setAnswer(null); setSearchResults(null);
    } catch (e) { setUploadStatus(`error:${e.message}`); }
    finally { setIndexing(false); }
  }

  async function handleAsk() {
    if (!query.trim() || !session) return;
    setAsking(true); setAnswer(null);
    try {
      const res = await fetch(`${API}/repo/ask`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ query, collection_name: session.collection_name, k: 5 }) });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail);
      setAnswer(data);
    } catch (e) { setAnswer({ error: e.message }); }
    finally { setAsking(false); }
  }

  async function handleSearch() {
    if (!searchQ.trim() || !session) return;
    setSearching(true); setSearchResults(null);
    try {
      const res = await fetch(`${API}/repo/search`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ query: searchQ, collection_name: session.collection_name, k: 5 }) });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail);
      setSearchResults(data);
    } catch (e) { setSearchResults({ error: e.message }); }
    finally { setSearching(false); }
  }

  async function handleSummary() {
    if (!session) return;
    setSummarizing(true); setSummary(null);
    try {
      const res = await fetch(`${API}/repo/summarize`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ query: "summarize", collection_name: session.collection_name }) });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail);
      setSummary(data);
    } catch (e) { setSummary({ error: e.message }); }
    finally { setSummarizing(false); }
  }

  async function handleCleanup() {
    if (!session) return;
    await fetch(`${API}/repo/session/${session.upload_id}`, { method: "DELETE" });
    setSession(null); setAnswer(null); setSearchResults(null); setSummary(null); setUploadStatus("");
  }

  const statusType = uploadStatus.split(":")[0];
  const statusMsg = uploadStatus.split(":").slice(1).join(":");
  const isHacker = theme === "hacker";

  return (
    <>
      <style>{isHacker ? hackerStyles : saasStyles}</style>
      <div className="app">
        <div className="header">
          <div className="logo">
            <div className="logo-title">{isHacker ? "CODEBASE.AI" : "Codebase Intelligence"}</div>
            <div className="logo-sub">{isHacker ? "SEMANTIC CODEBASE INTELLIGENCE" : "Semantic search & analysis for your codebase"}</div>
          </div>
          <div className="header-right">
            {session && <div className="session-badge">{isHacker ? "▣ " : ""}{session.collection_name}</div>}
            <button className="theme-toggle" onClick={() => setTheme(isHacker ? "saas" : "hacker")}>
              {isHacker ? "☀ Light" : "⬛ Dark"}
            </button>
          </div>
        </div>

        <div className={`upload-zone${drag ? " drag" : ""}`}
          onClick={() => fileRef.current.click()}
          onDragOver={e => { e.preventDefault(); setDrag(true); }}
          onDragLeave={() => setDrag(false)}
          onDrop={e => { e.preventDefault(); setDrag(false); handleUpload(e.dataTransfer.files[0]); }}>
          <input ref={fileRef} type="file" accept=".zip" onChange={e => handleUpload(e.target.files[0])} />
          <div className="upload-icon">⬆</div>
          <div className="upload-title">{uploading ? "Indexing..." : "Drop your codebase zip"}</div>
          <div className="upload-hint">click or drag · .zip only · auto-indexed on upload</div>
        </div>

        <div className="input-row" style={{marginBottom:"1rem"}}>
          <input className="input" placeholder="Or paste GitHub URL: https://github.com/user/repo"
            value={githubUrl} onChange={e => setGithubUrl(e.target.value)}
            onKeyDown={e => e.key === "Enter" && handleIndexUrl()} />
          <button className="btn btn-ghost" onClick={handleIndexUrl} disabled={indexing || !githubUrl.trim()}>
            {indexing ? "..." : "Clone"}
          </button>
        </div>

        {uploadStatus && (
          <div className={`status ${statusType}`}>
            {statusType === "loading" ? "⟳ " : statusType === "success" ? "✓ " : "✗ "}{statusMsg}
          </div>
        )}

        {session && (
          <div className="stats-row">
            <div className="stat"><div className="stat-val">{session.files_scanned}</div><div className="stat-label">files scanned</div></div>
            <div className="stat"><div className="stat-val">{session.chunks_found}</div><div className="stat-label">chunks indexed</div></div>
            <div className="stat"><div className="stat-val">{session.stored}</div><div className="stat-label">vectors stored</div></div>
            <button className="btn btn-danger" style={{marginLeft:"auto",alignSelf:"center"}} onClick={handleCleanup}>clear session</button>
          </div>
        )}

        {session && (
          <>
            <div className="tabs">
              {["ask", "search", "summary"].map(t => (
                <button key={t} className={`tab${tab === t ? " active" : ""}`} onClick={() => setTab(t)}>
                  {isHacker ? t.toUpperCase() : t.charAt(0).toUpperCase() + t.slice(1)}
                </button>
              ))}
            </div>

            {tab === "ask" && (
              <div>
                <div className="input-row">
                  <input className="input" placeholder="Ask anything about your codebase..." value={query} onChange={e => setQuery(e.target.value)} onKeyDown={e => e.key === "Enter" && handleAsk()} />
                  <button className="btn btn-primary" onClick={handleAsk} disabled={asking || !query.trim()}>{asking ? "..." : "Ask"}</button>
                </div>
                {answer && !answer.error && (
                  <>
                    <div className="answer-label">Answer</div>
                    <div className="answer-box">{answer.answer}</div>
                    {answer.sources?.length > 0 && (
                      <>
                        <div className="section-title">Sources ({answer.chunks_used})</div>
                        <div className="sources">
                          {answer.sources.map((s, i) => (
                            <div className="source-chip" key={i}>
                              <span className="source-file">{s.file}</span>
                              <span className="source-name">{s.name}</span>
                              <span className="source-score">{s.score}</span>
                            </div>
                          ))}
                        </div>
                      </>
                    )}
                  </>
                )}
                {answer?.error && <div className="status error">✗ {answer.error}</div>}
                {!answer && !asking && <div className="empty">Ask a question to get started</div>}
              </div>
            )}

            {tab === "search" && (
              <div>
                <div className="input-row">
                  <input className="input" placeholder="Search functions, classes, logic..." value={searchQ} onChange={e => setSearchQ(e.target.value)} onKeyDown={e => e.key === "Enter" && handleSearch()} />
                  <button className="btn btn-primary" onClick={handleSearch} disabled={searching || !searchQ.trim()}>{searching ? "..." : "Search"}</button>
                </div>
                {searchResults?.results?.map((r, i) => (
                  <div className="result-card" key={i}>
                    <div className="result-header">
                      <div className="result-name">{r.name}</div>
                      <span className="source-score">{r.score}</span>
                    </div>
                    <div className="result-meta">{r.file} · {r.type}{r.parent_class ? ` · ${r.parent_class}` : ""}</div>
                    {r.docstring && <div style={{fontSize:"0.8rem",color:"var(--muted)",marginBottom:"0.6rem",fontStyle:"italic"}}>{r.docstring}</div>}
                    <div className="code-block">{r.code}</div>
                  </div>
                ))}
                {searchResults?.error && <div className="status error">✗ {searchResults.error}</div>}
                {!searchResults && !searching && <div className="empty">Search your codebase semantically</div>}
              </div>
            )}

            {tab === "summary" && (
              <div>
                {!summary && (
                  <div style={{textAlign:"center", padding:"3rem 0"}}>
                    <button className="btn btn-primary" onClick={handleSummary} disabled={summarizing}>
                      {summarizing ? "Generating..." : "Generate Repository Summary"}
                    </button>
                  </div>
                )}
                {summary?.summary && (
                  <>
                    <div className="section-title">Repository Summary · {summary.files_found} files · {summary.total_chunks} chunks</div>
                    <div className="summary-box">{summary.summary}</div>
                    <div className="divider" />
                    <button className="btn btn-ghost" onClick={handleSummary} disabled={summarizing}>Regenerate</button>
                  </>
                )}
                {summary?.error && <div className="status error">✗ {summary.error}</div>}
              </div>
            )}
          </>
        )}

        {!session && !uploadStatus && (
          <div className="empty">
            {isHacker ? "upload a codebase zip to begin" : "Upload a codebase zip or paste a GitHub URL to get started"}
          </div>
        )}
      </div>
    </>
  );
}