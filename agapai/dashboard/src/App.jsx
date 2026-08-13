import { useState } from "react";
import DisasterDashboard from "./DisasterDashboard";
import NERTableView from "./NERTableView";
import NERMapView from "./NERMapView";

export default function App() {
  const [view, setView] = useState("table");

  return (
    <div>
      {view === "table" && (
        <DisasterDashboard view={view} setView={setView} />
      )}

      {view === "ner" && (
        <NERTableView view={view} setView={setView} />
      )}

      {view === "map" && (
        <NERMapView view={view} setView={setView} />
      )}
    </div>
  );
}