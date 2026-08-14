export default function Calamancy({ rows, onClose }) {
  return (
    <div style={{
      position: "fixed", top: 0, left: 0, right: 0, bottom: 0,
      background: "rgba(0,0,0,0.4)", display: "flex",
      alignItems: "center", justifyContent: "center", zIndex: 1000,
    }}>
      <div style={{
        background: "#fff", borderRadius: 8, padding: 20,
        width: "90%", maxWidth: 900, maxHeight: "80vh", overflowY: "auto",
      }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <h3>calamanCy — Retrieved Info</h3>
          <button onClick={onClose}>Close</button>
        </div>
        <p style={{ color: "#64748b", fontSize: 14 }}>
          Raw entities detected by the calamanCy NER model for each post,
          before any of our own filtering or geocoding runs.
        </p>

        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
          <thead>
            <tr style={{ background: "#eef2f7" }}>
              <th style={{ textAlign: "left", padding: 6 }}>Text</th>
              <th style={{ textAlign: "left", padding: 6 }}>Locations</th>
              <th style={{ textAlign: "left", padding: 6 }}>Persons</th>
              <th style={{ textAlign: "left", padding: 6 }}>Organizations</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row._id} style={{ borderBottom: "1px solid #e5e7eb" }}>
                <td style={{ padding: 6, maxWidth: 260 }}>{row.text}</td>
                <td style={{ padding: 6 }}>
                  {row.raw_locations_found && row.raw_locations_found.length > 0
                    ? row.raw_locations_found.join(", ")
                    : "None"}
                </td>
                <td style={{ padding: 6 }}>
                  {row.ner_persons && row.ner_persons.length > 0
                    ? row.ner_persons.join(", ")
                    : "None"}
                </td>
                <td style={{ padding: 6 }}>
                  {row.ner_organizations && row.ner_organizations.length > 0
                    ? row.ner_organizations.join(", ")
                    : "None"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}