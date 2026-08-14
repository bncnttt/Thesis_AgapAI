function parsePsgcBreadcrumb(breadcrumb) {
  if (!breadcrumb || breadcrumb.length === 0) {
    return { region: "None", province: "None", cityOrMunicipality: "None", barangay: "None" };
  }
  return {
    region: breadcrumb[0] || "None",
    province: breadcrumb[1] || "None",
    cityOrMunicipality: breadcrumb[2] || "None",
    barangay: breadcrumb[3] || "None",
  };
}

export default function PSGC({ rows, onClose }) {
  return (
    <div style={{
      position: "fixed", top: 0, left: 0, right: 0, bottom: 0,
      background: "rgba(0,0,0,0.4)", display: "flex",
      alignItems: "center", justifyContent: "center", zIndex: 1000,
    }}>
      <div style={{
        background: "#fff", borderRadius: 8, padding: 20,
        width: "95%", maxWidth: 1100, maxHeight: "80vh", overflowY: "auto",
      }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <h3>PSGC — Retrieved Info</h3>
          <button onClick={onClose}>Close</button>
        </div>
        <p style={{ color: "#64748b", fontSize: 14 }}>
          Region, province, city/municipality, barangay, and PSGC code retrieved
          for each post's resolved location. Posts matched to a landmark
          (not an official PSGC entry) or left unresolved show None.
        </p>

        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
          <thead>
            <tr style={{ background: "#eef2f7" }}>
              <th style={{ textAlign: "left", padding: 6 }}>Text</th>
              <th style={{ textAlign: "left", padding: 6 }}>Region</th>
              <th style={{ textAlign: "left", padding: 6 }}>Province</th>
              <th style={{ textAlign: "left", padding: 6 }}>City/Municipality</th>
              <th style={{ textAlign: "left", padding: 6 }}>Barangay</th>
              <th style={{ textAlign: "left", padding: 6 }}>PSGC Code</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const coords = row.ner_coordinates;
              const isAmbiguous = coords?.ambiguous;
              const parsed = coords && !isAmbiguous
                ? parsePsgcBreadcrumb(coords.breadcrumb)
                : { region: "None", province: "None", cityOrMunicipality: "None", barangay: "None" };
              const psgcCode = coords && !isAmbiguous ? (coords.psgc_code || "None") : "None";

              return (
                <tr key={row._id} style={{ borderBottom: "1px solid #e5e7eb" }}>
                  <td style={{ padding: 6, maxWidth: 220 }}>{row.text}</td>
                  <td style={{ padding: 6 }}>{parsed.region}</td>
                  <td style={{ padding: 6 }}>{parsed.province}</td>
                  <td style={{ padding: 6 }}>{parsed.cityOrMunicipality}</td>
                  <td style={{ padding: 6 }}>{parsed.barangay}</td>
                  <td style={{ padding: 6 }}>
                    {isAmbiguous
                      ? `Ambiguous (${coords.candidate_count} matches)`
                      : psgcCode}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}