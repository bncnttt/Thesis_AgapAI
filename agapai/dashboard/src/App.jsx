import { useState } from "react";
import DisasterDashboard from "./DisasterDashboard";
import NERTableView from "./NERTableView";
import NERMapView from "./NERMapView";

export default function App() {
  const [view, setView] = useState("table");

  return (
    <div>
      <div style={{ padding: 10, display: "flex", gap: 8 }}>
        <button onClick={() => setView("table")}>Posts Table</button>
        <button onClick={() => setView("ner")}>NER Info</button>
        <button onClick={() => setView("map")}>Map View</button>
      </div>
      {view === "table" && <DisasterDashboard />}
      {view === "ner" && <NERTableView />}
      {view === "map" && <NERMapView />}
    </div>
  );
}