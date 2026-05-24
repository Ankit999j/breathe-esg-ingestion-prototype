import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import { CheckCircle2, Database, FileUp, Lock, RefreshCw, Search, XCircle } from "lucide-react";
import "./styles.css";

const API = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api";
const AUTH = "Basic " + btoa("analyst@acme.example:demo12345");

async function api(path, options = {}) {
  const response = await fetch(`${API}${path}`, {
    ...options,
    headers: {
      Authorization: AUTH,
      ...(options.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
      ...(options.headers || {}),
    },
  });
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

function Pill({ value }) {
  return <span className={`pill ${value}`}>{String(value).replace("_", " ")}</span>;
}

function App() {
  const [me, setMe] = useState(null);
  const [dashboard, setDashboard] = useState(null);
  const [sources, setSources] = useState([]);
  const [batches, setBatches] = useState([]);
  const [activities, setActivities] = useState([]);
  const [selected, setSelected] = useState(null);
  const [status, setStatus] = useState("");
  const [query, setQuery] = useState("");
  const [uploadSource, setUploadSource] = useState("");
  const [file, setFile] = useState(null);
  const [error, setError] = useState("");

  async function refresh() {
    try {
      setError("");
      const [user, dash, src, batch, rows] = await Promise.all([
        api("/me/"),
        api("/dashboard/"),
        api("/sources/"),
        api("/batches/"),
        api(`/activities/${status ? `?status=${status}` : ""}`),
      ]);
      setMe(user);
      setDashboard(dash);
      setSources(src);
      setBatches(batch);
      setActivities(rows);
      setSelected((current) => current ? rows.find((row) => row.id === current.id) || rows[0] : rows[0]);
    } catch (err) {
      setError(`Could not load backend data from ${API}. Check that Django is running on port 8000. ${err.message}`);
    }
  }

  useEffect(() => { refresh(); }, [status]);

  const filtered = useMemo(() => {
    const needle = query.toLowerCase();
    return activities.filter((row) => [row.external_id, row.category, row.description, row.facility_code, row.supplier_or_vendor].join(" ").toLowerCase().includes(needle));
  }, [activities, query]);

  async function upload() {
    if (!uploadSource || !file) return;
    const form = new FormData();
    form.append("source_system", uploadSource);
    form.append("file", file);
    await api("/batches/upload/", { method: "POST", body: form });
    setFile(null);
    await refresh();
  }

  async function action(name) {
    if (!selected) return;
    const updated = await api(`/activities/${selected.id}/${name}/`, { method: "POST", body: JSON.stringify({}) });
    setSelected(updated);
    await refresh();
  }

  return (
    <main>
      <aside>
        <div className="brand"><Database size={22} /> Breathe ESG</div>
        <div className="tenant">{me?.tenant?.name || "Demo tenant"}</div>
        <button onClick={refresh}><RefreshCw size={16} /> Refresh</button>
        <label>Status</label>
        <select value={status} onChange={(event) => setStatus(event.target.value)}>
          <option value="">All rows</option>
          <option value="imported">Imported</option>
          <option value="suspicious">Suspicious</option>
          <option value="failed">Failed</option>
          <option value="approved">Approved</option>
          <option value="locked">Locked</option>
        </select>
        <section className="upload">
          <h2>Upload</h2>
          <select value={uploadSource} onChange={(event) => setUploadSource(event.target.value)}>
            <option value="">Choose source</option>
            {sources.map((source) => <option key={source.id} value={source.id}>{source.name}</option>)}
          </select>
          <input type="file" accept=".csv" onChange={(event) => setFile(event.target.files[0])} />
          <button onClick={upload}><FileUp size={16} /> Import CSV</button>
          {error && <p className="error">{error}</p>}
        </section>
      </aside>

      <section className="workspace">
        <header>
          <div>
            <h1>Analyst Review</h1>
            <p>Normalize, investigate, approve, and lock activity data before audit.</p>
          </div>
          <div className="search"><Search size={16} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search rows" /></div>
        </header>

        <div className="metrics">
          {(dashboard?.by_status || []).map((item) => <div className="metric" key={item.review_status}><span>{item.review_status}</span><strong>{item.count}</strong></div>)}
          {(dashboard?.by_scope || []).map((item) => <div className="metric" key={item.scope}><span>{item.scope}</span><strong>{item.count}</strong></div>)}
        </div>

        <div className="split">
          <section className="table">
            <table>
              <thead>
                <tr><th>Source</th><th>External ID</th><th>Scope</th><th>Category</th><th>CO2e</th><th>Status</th></tr>
              </thead>
              <tbody>
                {filtered.map((row) => (
                  <tr key={row.id} className={selected?.id === row.id ? "active" : ""} onClick={() => setSelected(row)}>
                    <td>{row.source_type}</td>
                    <td>{row.external_id || "missing"}</td>
                    <td>{row.scope}</td>
                    <td>{row.category}</td>
                    <td>{row.estimated_kg_co2e || "-"}</td>
                    <td><Pill value={row.review_status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>

          <Detail selected={selected} onApprove={() => action("approve")} onReject={() => action("reject")} onLock={() => action("lock")} />
        </div>

        <section className="batches">
          <h2>Import Batches</h2>
          {batches.slice(0, 6).map((batch) => (
            <div key={batch.id} className="batch">
              <span>{batch.source_name}</span>
              <span>{batch.original_filename}</span>
              <span>{batch.total_rows} rows</span>
              <span>{batch.suspicious_rows} suspicious</span>
              <span>{batch.failed_rows} failed</span>
            </div>
          ))}
        </section>
      </section>
    </main>
  );
}

function Detail({ selected, onApprove, onReject, onLock }) {
  if (!selected) return <section className="detail"><p>No row selected.</p></section>;
  return (
    <section className="detail">
      <div className="detailHeader">
        <div>
          <h2>{selected.external_id || "Unidentified row"}</h2>
          <Pill value={selected.review_status} />
        </div>
        <div className="actions">
          <button onClick={onApprove}><CheckCircle2 size={16} /> Approve</button>
          <button onClick={onReject}><XCircle size={16} /> Reject</button>
          <button onClick={onLock}><Lock size={16} /> Lock</button>
        </div>
      </div>
      <dl>
        <dt>Source</dt><dd>{selected.source_name}</dd>
        <dt>Date / Period</dt><dd>{selected.activity_date || `${selected.period_start} to ${selected.period_end}`}</dd>
        <dt>Original</dt><dd>{selected.original_quantity} {selected.original_unit}</dd>
        <dt>Normalized</dt><dd>{selected.normalized_quantity || "-"} {selected.normalized_unit}</dd>
        <dt>Estimated emissions</dt><dd>{selected.estimated_kg_co2e || "-"} kg CO2e</dd>
        <dt>Facility</dt><dd>{selected.facility_code || "-"}</dd>
        <dt>Description</dt><dd>{selected.description || "-"}</dd>
      </dl>
      <h3>Validation Flags</h3>
      <div className="flags">{selected.validation_flags.length ? selected.validation_flags.map((flag) => <Pill key={flag} value={flag} />) : "None"}</div>
      <h3>Audit Trail</h3>
      <ol>
        {selected.audit_events.map((event) => <li key={event.id}><strong>{event.event_type}</strong> {event.message}</li>)}
      </ol>
    </section>
  );
}

createRoot(document.getElementById("root")).render(<App />);
