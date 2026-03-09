import { useState, useRef } from "react";
import "./App.css";

function App() {
  const [studyContext, setStudyContext] = useState("");
  const [variables, setVariables] = useState([""]);
  const [mrns, setMrns] = useState("");
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [currentMrn, setCurrentMrn] = useState("");
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState("");
  const [showResults, setShowResults] = useState(false);
  const resultsRef = useRef(null);

  const addVariable = () => setVariables([...variables, ""]);

  const updateVariable = (index, value) => {
    const updated = [...variables];
    updated[index] = value;
    setVariables(updated);
  };

  const removeVariable = (index) => {
    if (variables.length > 1) {
      setVariables(variables.filter((_, i) => i !== index));
    }
  };

  const runExtraction = async () => {
    setError("");
    setResults([]);
    setShowResults(false);
    setLoading(true);
    setProgress(0);

    const mrnList = mrns.split("\n").map((m) => m.trim()).filter(Boolean);
    const varList = variables.filter((v) => v.trim());

    if (!mrnList.length || !varList.length || !studyContext.trim()) {
      setError("Please fill in study description, at least one variable, and at least one MRN.");
      setLoading(false);
      return;
    }

    const allResults = [];

    for (let i = 0; i < mrnList.length; i++) {
      const mrn = mrnList[i];
      setCurrentMrn(mrn);
      setProgress(((i) / mrnList.length) * 100);
      try {
        const resp = await fetch("http://localhost:5001/api/extract", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ mrn, study_context: studyContext, variables: varList }),
        });
        const data = await resp.json();
        if (data.error) {
          allResults.push({ mrn, results: [], error: data.error });
        } else {
          allResults.push(data);
        }
      } catch (e) {
        allResults.push({ mrn, results: [], error: e.message });
      }
      setResults([...allResults]);
    }

    setProgress(100);
    setCurrentMrn("");
    setLoading(false);
    setShowResults(true);
    setTimeout(() => resultsRef.current?.scrollIntoView({ behavior: "smooth" }), 100);
  };

  const downloadCsv = () => {
    const rows = [["MRN", "Variable", "Value", "Source", "Confidence", "Notes"]];
    for (const r of results) {
      for (const v of r.results || []) {
        rows.push([r.mrn, v.variable || "", v.value || "", v.source || "", v.confidence || "", v.notes || ""]);
      }
    }
    const csv = rows.map((r) => r.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "extraction_results.csv";
    a.click();
    URL.revokeObjectURL(url);
  };

  const totalVars = results.reduce((sum, r) => sum + (r.results?.length || 0), 0);
  const highConf = results.reduce((sum, r) => sum + (r.results?.filter((v) => v.confidence === "high").length || 0), 0);

  return (
    <div className="app-wrapper">
      {/* Background effects */}
      <div className="bg-glow bg-glow-1" />
      <div className="bg-glow bg-glow-2" />
      <div className="bg-grid" />

      {/* Header */}
      <header className="header">
        <div className="logo">
          <div className="logo-icon">A</div>
          <span>Avyra</span>
        </div>
        <div className="header-badge">Chart Extraction</div>
      </header>

      {/* Hero */}
      <section className="hero">
        <h1>
          <span className="hero-accent">AI-Powered</span> Retrospective
          <br />Chart Extraction
        </h1>
        <p className="hero-sub">
          Extract clinical variables from Epic EHR data using FHIR APIs and Claude.
          <br />Define your study, add patient MRNs, and let the agent do the work.
        </p>
      </section>

      {/* Main form */}
      <main className="main-content">
        <div className="form-card">
          <div className="form-section">
            <label className="form-label">
              <span className="label-icon">01</span>
              Study Description
            </label>
            <textarea
              className="input-field textarea"
              value={studyContext}
              onChange={(e) => setStudyContext(e.target.value)}
              placeholder="Describe the retrospective study being conducted..."
              rows={3}
            />
          </div>

          <div className="form-section">
            <label className="form-label">
              <span className="label-icon">02</span>
              Variables to Extract
            </label>
            <div className="variables-list">
              {variables.map((v, i) => (
                <div key={i} className="variable-row">
                  <div className="variable-index">{i + 1}</div>
                  <input
                    className="input-field"
                    type="text"
                    value={v}
                    onChange={(e) => updateVariable(i, e.target.value)}
                    placeholder={`e.g. calcium_channel_blocker_and_dose`}
                  />
                  {variables.length > 1 && (
                    <button className="btn-icon btn-remove" onClick={() => removeVariable(i)}>
                      <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                        <path d="M11 3L3 11M3 3l8 8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                      </svg>
                    </button>
                  )}
                </div>
              ))}
            </div>
            <button className="btn-add" onClick={addVariable}>
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                <path d="M7 1v12M1 7h12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
              </svg>
              Add Variable
            </button>
          </div>

          <div className="form-section">
            <label className="form-label">
              <span className="label-icon">03</span>
              Patient MRNs
            </label>
            <textarea
              className="input-field textarea"
              value={mrns}
              onChange={(e) => setMrns(e.target.value)}
              placeholder={"203010\n203011\n203039"}
              rows={3}
            />
            <p className="form-hint">One MRN per line. Each will be processed sequentially by the extraction agent.</p>
          </div>

          {error && (
            <div className="error-banner">
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <circle cx="8" cy="8" r="7" stroke="currentColor" strokeWidth="1.5" />
                <path d="M8 5v3.5M8 10.5v.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
              </svg>
              {error}
            </div>
          )}

          <button className="btn-run" onClick={runExtraction} disabled={loading}>
            {loading ? (
              <div className="btn-loading">
                <div className="spinner" />
                <span>Extracting {currentMrn}...</span>
              </div>
            ) : (
              <>
                Run Extraction
                <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
                  <path d="M3.75 9h10.5M9.75 4.5L14.25 9l-4.5 4.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </>
            )}
          </button>

          {loading && (
            <div className="progress-bar-wrapper">
              <div className="progress-bar">
                <div className="progress-fill" style={{ width: `${progress}%` }} />
              </div>
              <span className="progress-text">{Math.round(progress)}%</span>
            </div>
          )}
        </div>

        {/* Results */}
        {results.length > 0 && (
          <div className="results-section" ref={resultsRef}>
            <div className="results-header">
              <div>
                <h2>Extraction Results</h2>
                <p className="results-meta">
                  {results.length} patient{results.length !== 1 ? "s" : ""} processed
                  &middot; {totalVars} variable{totalVars !== 1 ? "s" : ""} extracted
                  &middot; {highConf} high confidence
                </p>
              </div>
              <button className="btn-download" onClick={downloadCsv}>
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                  <path d="M2 11v2a1 1 0 001 1h10a1 1 0 001-1v-2M8 2v8.5M4.5 7L8 10.5 11.5 7" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                Download CSV
              </button>
            </div>

            <div className="results-table-wrapper">
              <table className="results-table">
                <thead>
                  <tr>
                    <th>MRN</th>
                    <th>Variable</th>
                    <th>Value</th>
                    <th>Source</th>
                    <th>Confidence</th>
                    <th>Notes</th>
                  </tr>
                </thead>
                <tbody>
                  {results.flatMap((r) =>
                    (r.results || []).map((v, i) => (
                      <tr key={`${r.mrn}-${i}`}>
                        <td><span className="mrn-chip">{r.mrn}</span></td>
                        <td className="var-name">{v.variable}</td>
                        <td className="value-cell">{v.value}</td>
                        <td className="source-cell">{v.source}</td>
                        <td>
                          <span className={`confidence-badge ${v.confidence}`}>
                            {v.confidence}
                          </span>
                        </td>
                        <td className="notes-cell">{v.notes}</td>
                      </tr>
                    ))
                  )}
                  {results.filter((r) => r.error).map((r) => (
                    <tr key={`${r.mrn}-err`} className="error-row">
                      <td><span className="mrn-chip">{r.mrn}</span></td>
                      <td colSpan={5} className="error-cell">{r.error}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </main>

      <footer className="footer">
        <span>Built with FHIR R4 + Claude</span>
        <span className="footer-dot">&middot;</span>
        <span>Avyra</span>
      </footer>
    </div>
  );
}

export default App;
