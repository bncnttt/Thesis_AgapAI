import { useMemo, useRef, useState } from "react";

const API_ENDPOINT = "http://127.0.0.1:8000/disaster-alerts";
const LIVE_SEARCH_LIMIT = 50;
const ROW_LIMITS = [10, 20, 25, 50, 100];

const POST_COLUMNS = [
  ["_id", "_id"],
  ["author_did", "author_did"],
  ["author_handle", "author_handle"],
  ["posted_by", "posted_by"],
  ["text", "text"],
  ["disaster_post_text", "disaster_post_text"],
  ["retrieval_source", "retrieval_source"],
  ["search_query", "search_query"],
  ["created_at", "created_at"],
  ["time_created_readable", "time_created_readable"],
  ["collected_at", "collected_at"],
  ["time_collected_readable", "time_collected_readable"],
  ["keyword_matched", "keyword_matched"],
  ["reply_count", "reply_count"],
  ["repost_count", "repost_count"],
  ["like_count", "like_count"],
  ["has_location_clue", "has_location_clue"],
  ["location_name", "location_name"],
  ["processed", "processed"],
  ["social_graph", "social_graph"],
];

const USER_COLUMNS = [
  ["_id", "_id"],
  ["handle", "handle"],
  ["display_name", "display_name"],
  ["follower_count", "follower_count"],
  ["following_count", "following_count"],
  ["mutual_tie_count", "mutual_tie_count"],
  ["followers", "followers"],
  ["following", "following"],
  ["mutual_ties", "mutual_ties"],
  ["fetched_at", "fetched_at"],
];

function formatValue(value) {
  if (value === null || value === undefined) {
    return "";
  }

  if (Array.isArray(value)) {
    return value.length ? value.join(", ") : "[]";
  }

  if (typeof value === "object") {
    return JSON.stringify(value);
  }

  return String(value);
}

function sortByNewestDate(rows, dateKey) {
  return [...rows].sort((firstRow, secondRow) => {
    const firstTime = Date.parse(firstRow[dateKey] || "");
    const secondTime = Date.parse(secondRow[dateKey] || "");

    if (Number.isNaN(firstTime) && Number.isNaN(secondTime)) {
      return 0;
    }
    if (Number.isNaN(firstTime)) {
      return 1;
    }
    if (Number.isNaN(secondTime)) {
      return -1;
    }
    return secondTime - firstTime;
  });
}

export default function DisasterDashboard() {
  const [activeCollection, setActiveCollection] = useState("posts");
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");
  const [posts, setPosts] = useState([]);
  const [users, setUsers] = useState([]);
  const [rowsPerPage, setRowsPerPage] = useState(20);
  const [currentPage, setCurrentPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const abortControllerRef = useRef(null);

  const columns = activeCollection === "posts" ? POST_COLUMNS : USER_COLUMNS;
  const rows = activeCollection === "posts" ? posts : users;
  const totalRows = rows.length;
  const totalPages = Math.max(1, Math.ceil(totalRows / rowsPerPage));
  const startIndex = totalRows === 0 ? 0 : (currentPage - 1) * rowsPerPage + 1;
  const endIndex = Math.min(currentPage * rowsPerPage, totalRows);
  const canLoadData = Boolean(fromDate && toDate) && !loading;

  const pageRows = useMemo(() => {
    const first = (currentPage - 1) * rowsPerPage;
    return rows.slice(first, first + rowsPerPage);
  }, [rows, currentPage, rowsPerPage]);

  async function fetchData() {
    if ((fromDate && !toDate) || (!fromDate && toDate)) {
      setError("Select both From and To dates, or leave both empty.");
      return;
    }

    if (fromDate && toDate && fromDate > toDate) {
      setError("From date must be earlier than or equal to To date.");
      return;
    }

    setLoading(true);
    setError("");
    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    try {
      const params = new URLSearchParams();
      if (fromDate && toDate) {
        params.set("start", fromDate);
        params.set("end", toDate);
      }
      // Always ask the API to pull fresh data straight from Bluesky rather
      // than silently falling back to whatever is already cached in Mongo.
      params.set("force_refresh", "true");
      params.set("include_graph", "false");
      params.set("search_limit", String(LIVE_SEARCH_LIMIT));

      const response = await fetch(`${API_ENDPOINT}?${params.toString()}`, {
        signal: abortController.signal,
      });
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || `Request failed with status ${response.status}`);
      }

      if (abortController.signal.aborted) {
        return;
      }

      const nextPosts = sortByNewestDate(data.posts_collection || [], "created_at");
      const nextUsers = sortByNewestDate(data.users_collection || [], "fetched_at");
      setPosts(nextPosts);
      setUsers(nextUsers);
      setCurrentPage(1);
      if (nextPosts.length === 0 && nextUsers.length === 0) {
        setError("The API finished loading, but no matching data was found for the selected dates.");
      }
    } catch (fetchError) {
      if (fetchError.name === "AbortError") {
        setError("");
        return;
      }

      setError(fetchError.message || "Failed to load data.");
    } finally {
      if (abortControllerRef.current === abortController) {
        abortControllerRef.current = null;
        setLoading(false);
      }
    }
  }

  function cancelLoad() {
    abortControllerRef.current?.abort();
  }

  function selectCollection(collection) {
    setActiveCollection(collection);
    setCurrentPage(1);
  }

  function handleRowsPerPageChange(event) {
    setRowsPerPage(Number(event.target.value));
    setCurrentPage(1);
  }

  return (
    <main className="dashboard">
      <header className="dashboard-header">
        <h1>AgapAI Dashboard</h1>
        <p>MongoDB saved disaster data</p>
      </header>

      <section className="toolbar" aria-label="Dashboard controls">
        <div className="view-buttons">
          <button
            type="button"
            className={activeCollection === "posts" ? "active" : ""}
            onClick={() => selectCollection("posts")}
          >
            Posts
          </button>
          <button
            type="button"
            className={activeCollection === "users" ? "active" : ""}
            onClick={() => selectCollection("users")}
          >
            Users
          </button>
        </div>

        <label>
          From
          <input
            type="date"
            value={fromDate}
            onChange={(event) => setFromDate(event.target.value)}
          />
        </label>

        <label>
          To
          <input
            type="date"
            value={toDate}
            onChange={(event) => setToDate(event.target.value)}
          />
        </label>

        <div className="load-controls">
          <button type="button" onClick={() => fetchData()} disabled={!canLoadData}>
            {loading ? "Loading..." : "Load Data"}
          </button>
          <button
            type="button"
            className="cancel-button"
            onClick={cancelLoad}
            disabled={!loading}
          >
            Cancel
          </button>
        </div>
      </section>

      {error && <div className="status error">{error}</div>}
      {loading && (
        <div className="status loading">
          Please wait. Collecting data from bluesky.
        </div>
      )}

      <section className="table-actions" aria-label="Table controls">
        <div className="row-count">
          Showing {startIndex}-{endIndex} of {totalRows} {activeCollection}
        </div>

        <label>
          Rows
          <select value={rowsPerPage} onChange={handleRowsPerPageChange}>
            {ROW_LIMITS.map((limit) => (
              <option key={limit} value={limit}>
                {limit}
              </option>
            ))}
          </select>
        </label>

        <div className="pager">
          <button
            type="button"
            onClick={() => setCurrentPage((page) => Math.max(1, page - 1))}
            disabled={currentPage === 1 || loading}
          >
            Prev
          </button>
          <span>
            Page {currentPage} of {totalPages}
          </span>
          <button
            type="button"
            onClick={() => setCurrentPage((page) => Math.min(totalPages, page + 1))}
            disabled={currentPage === totalPages || loading}
          >
            Next
          </button>
        </div>
      </section>

      <section className="table-wrap" aria-label={`${activeCollection} data`}>
        <table>
          <thead>
            <tr>
              <th>#</th>
              {columns.map(([key, label]) => (
                <th key={key}>{label}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {pageRows.length === 0 && !loading ? (
              <tr>
                <td colSpan={columns.length + 1} className="empty">
                  No data found.
                </td>
              </tr>
            ) : (
              pageRows.map((row, index) => (
                <tr key={row._id || `${activeCollection}-${currentPage}-${index}`}>
                  <td>{(currentPage - 1) * rowsPerPage + index + 1}</td>
                  {columns.map(([key]) => (
                    <td key={key}>{formatValue(row[key])}</td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </section>
    </main>
  );
}
