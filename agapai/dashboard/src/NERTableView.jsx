import { useEffect, useState } from "react";
import Calamancy from "./Calamancy";
import PSGC from "./PSGC";

const API_BASE = "http://127.0.0.1:8000";

function formatDateTime(datetimeInfo) {
  if (!datetimeInfo) return "None";
  if (datetimeInfo.source === "extracted_from_text") {
    return datetimeInfo.expressions
      .map((e) => `${e.raw_phrase} (${e.normalized_datetime || "unresolved"})`)
      .join(", ");
  }
  return datetimeInfo.fallback_readable
    ? `${datetimeInfo.fallback_readable} (from post's actual timestamp)`
    : "None";
}

function formatLocation(coords) {
  if (!coords) return "None";
  if (coords.ambiguous) return `Ambiguous (${coords.candidate_count} possible matches)`;
  return coords.matched_name || "None";
}

export default function NERTableContent() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [showCalamancy, setShowCalamancy] = useState(false);
  const [showPsgc, setShowPsgc] = useState(false);

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
    <>
      <section className="toolbar" style={{ marginTop: -4 }}>
        <button type="button" onClick={() => setShowCalamancy(true)} style={{ fontSize: 12, padding: "4px 10px" }}>
          calamanCy Info
        </button>
        <button type="button" onClick={() => setShowPsgc(true)} style={{ fontSize: 12, padding: "4px 10px" }}>
          PSGC Info
        </button>
      </section>

      {error && <div className="status error">{error}</div>}
      {loading && <div className="status loading">Running NER on posts, please wait.</div>}

      <section className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Text</th>
              <th>Handle</th>
              <th>Posted By</th>
              <th>Location</th>
              <th>Date/Time</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && !loading ? (
              <tr><td colSpan={5} className="empty">No processed posts yet.</td></tr>
            ) : (
              rows.map((row) => (
                <tr key={row._id}>
                  <td>{row.text}</td>
                  <td>{row.author_handle || "None"}</td>
                  <td>{row.posted_by || "None"}</td>
                  <td>{formatLocation(row.ner_coordinates)}</td>
                  <td>{formatDateTime(row.ner_datetime)}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </section>

      {showCalamancy && <Calamancy rows={rows} onClose={() => setShowCalamancy(false)} />}
      {showPsgc && <PSGC rows={rows} onClose={() => setShowPsgc(false)} />}
    </>
  );
}