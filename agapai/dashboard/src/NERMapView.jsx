import { useEffect, useState } from "react";
import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import NERPanel from "./NERPanel";

const API_BASE = "http://127.0.0.1:8000";
const CEBU_CENTER = [10.3157, 123.8854];

export default function NERMapView({ view, setView }) {
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [selectedPostId, setSelectedPostId] = useState(null);

  async function loadMapData() {
    setLoading(true);
    setError("");

    try {
      await fetch(`${API_BASE}/ner/process-all`, { method: "POST" });

      const response = await fetch(`${API_BASE}/ner/map-data`);
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Failed to load map data.");
      }

      setPosts(data.posts || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadMapData();
  }, []);

  return (
    <main className="dashboard">
      <header className="dashboard-header">
        <h1>Map View</h1>
        <p>Mapped NER locations from disaster posts</p>
      </header>

      <section className="toolbar">
        <div className="navigation-buttons">
          <button
            type="button"
            className={view === "table" ? "active" : ""}
            onClick={() => setView("table")}
          >
            Posts Table
          </button>

          <button
            type="button"
            className={view === "ner" ? "active" : ""}
            onClick={() => setView("ner")}
          >
            NER Info
          </button>

          <button
            type="button"
            className={view === "map" ? "active" : ""}
            onClick={() => setView("map")}
          >
            Map View
          </button>
        </div>

        <button type="button" onClick={loadMapData} disabled={loading}>
          {loading ? "Processing..." : "Refresh Map"}
        </button>
      </section>

      {error && <div className="status error">{error}</div>}

      <MapContainer
        center={CEBU_CENTER}
        zoom={10}
        style={{ height: "600px", width: "100%" }}
      >
        <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />

        {posts.map((post) => {
          const coords = post.ner_coordinates;

          if (!coords || coords.ambiguous) return null;

          return (
            <Marker key={post._id} position={[coords.latitude, coords.longitude]}>
              <Popup>
                <div>
                  <p>
                    <strong>{post.posted_by}</strong>
                  </p>
                  <p>{post.text}</p>
                  <p>
                    <em>Location: {coords.matched_name}</em>
                  </p>
                  <button type="button" onClick={() => setSelectedPostId(post._id)}>
                    Show NER Process
                  </button>
                </div>
              </Popup>
            </Marker>
          );
        })}
      </MapContainer>

      {selectedPostId && (
        <NERPanel
          postId={selectedPostId}
          onClose={() => setSelectedPostId(null)}
        />
      )}
    </main>
  );
}