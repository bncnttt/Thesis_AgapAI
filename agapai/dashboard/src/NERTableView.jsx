import { useEffect, useState } from "react";

const API_BASE = "http://127.0.0.1:8000";

export default function NERTableView() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function loadData() {
    setLoading(true);
    setError("");
    try {
      await fetch(`${API_BASE}/ner/process-all`, { method: "POST" });

      const response = await fetch(`${API_BASE}/ner/table-data`);
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Failed to load NER data.");
      setRows(data.rows || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  return (
    <main className="dashboard">
      <header className="dashboard-header">
        <h1>NER Info</h1>
        <p>Extracted locations, date/time, and entities per post</p>
      </header>

      <section className="toolbar">
        <button type="button" onClick={loadData} disabled={loading}>
          {loading ? "Processing..." : "Refresh"}
        </button>
      </section>

      {error && <div className="status error">{error}</div>}
      {loading && <div className="status loading">Running NER on posts, please wait.</div>}

      <section className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Text</th>
              <th>Posted By</th>
              <th>Location</th>
              <th>Date/Time</th>
              <th>Persons</th>
              <th>Organizations</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && !loading ? (
              <tr>
                <td colSpan={6} className="empty">No processed posts yet.</td>
              </tr>
            ) : (
              rows.map((row) => (
                <tr key={row._id}>
                  <td>{row.text}</td>
                  <td>{row.posted_by}</td>
                  <td>{JSON.stringify(row.location)}</td>
                  <td>{JSON.stringify(row.datetime)}</td>
                  <td>{JSON.stringify(row.persons)}</td>
                  <td>{JSON.stringify(row.organizations)}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </section>
    </main>
  );
}