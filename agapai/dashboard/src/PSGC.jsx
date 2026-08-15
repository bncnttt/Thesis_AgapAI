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

// When a location is ambiguous, every candidate still shares the same
// deepest-level name (e.g. all 4 "San Roque" candidates ARE "San Roque" --
// they only disagree on which municipality it's in). This pulls out
// whatever's actually consistent across all candidates instead of
// blanking the whole row just because the city/municipality is unknown.
function parseAmbiguousCandidates(candidates) {
  if (!candidates || candidates.length === 0) {
    return { region: "None", province: "None", cityOrMunicipality: "Ambiguous", barangay: "None" };
  }

  const allSame = (index) => {
    const first = candidates[0][index];
    return candidates.every((c) => c[index] === first) ? first : null;
  };

  const deepestLevel = Math.max(...candidates.map((c) => c.length)) - 1;

  return {
    region: allSame(0) || "None",
    province: allSame(1) || "None",
    cityOrMunicipality: "Ambiguous",
    barangay: deepestLevel >= 3 ? (allSame(deepestLevel) || "None") : "None",
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
          for each post's resolved location. When a location is ambiguous, only
          the city/municipality is unresolved -- shared fields (region, province,
          barangay name) are still shown since every candidate agrees on them.
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

              let parsed;
              let psgcCode;

              if (isAmbiguous) {
                parsed = parseAmbiguousCandidates(coords.candidates);
                psgcCode = `Ambiguous (${coords.candidate_count} matches)`;
              } else if (coords) {
                parsed = parsePsgcBreadcrumb(coords.breadcrumb);
                psgcCode = coords.psgc_code || "None";
              } else {
                parsed = { region: "None", province: "None", cityOrMunicipality: "None", barangay: "None" };
                psgcCode = "None";
              }

              return (
                <tr key={row._id} style={{ borderBottom: "1px solid #e5e7eb" }}>
                  <td style={{ padding: 6, maxWidth: 220 }}>{row.text}</td>
                  <td style={{ padding: 6 }}>{parsed.region}</td>
                  <td style={{ padding: 6 }}>{parsed.province}</td>
                  <td style={{ padding: 6 }}>{parsed.cityOrMunicipality}</td>
                  <td style={{ padding: 6 }}>{parsed.barangay}</td>
                  <td style={{ padding: 6 }}>{psgcCode}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}