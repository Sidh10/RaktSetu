import { useEffect, useState } from "react";
import { get } from "../api.js";

const AGE = ["today", "1 day old", "2+ days old"];

export default function TrustView() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    get("/api/trust").then(setData).catch((e) => setError(e.message));
  }, []);

  if (error) return <div className="alert">{error}</div>;
  if (!data) return <p className="small">Loading…</p>;
  return (
    <section className="panel" aria-label="Report trust">
      <h3>Report trust by centre and listing age</h3>
      <p className="small">{data.note}</p>
      <div className="table-scroll">
        <table>
          <thead>
            <tr><th>Centre</th><th>Listing age</th><th>α</th><th>β</th><th>Estimate</th><th>Band</th><th>Seeded history (simulated)</th><th>Confirmations here</th></tr>
          </thead>
          <tbody>
            {data.rows.map((r) => (
              <tr key={`${r.centre}-${r.bucket}`} className={r.current ? "mine" : ""}>
                <td>{r.bucket === 0 ? <span className="cn">{r.name}</span> : ""}</td>
                <td>{AGE[r.bucket]}{r.current ? " · current" : ""}</td>
                <td className="num">{r.alpha}</td>
                <td className="num">{r.beta}</td>
                <td className="num">{r.p.toFixed(2)}</td>
                <td><span className={`band ${r.band}`}>{r.band}</span></td>
                <td className="small">+{r.seeded_alpha} found / +{r.seeded_beta} missing</td>
                <td className="num">{r.n_confirmations}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="note">
        Estimate = α / (α + β), starting from a Beta(2,1) prior. Each confirmation adds units found to α and units missing
        to β. There is no decay: every outcome counts equally. Internal view only; the public finder shows bands, not
        these numbers.
      </div>
    </section>
  );
}
