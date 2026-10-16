import { useState } from "react";
import { GROUPS, get } from "../api.js";

// Public page: no login, bands only, never a percentage per centre (docs/CLAIMS_AND_LIMITS.md section 5).
export default function Finder() {
  const [group, setGroup] = useState("O+");
  const [component, setComponent] = useState("RDP");
  const [res, setRes] = useState(null);
  const [error, setError] = useState("");

  const search = async (e) => {
    e.preventDefault();
    setError("");
    try {
      setRes(await get("/api/public/finder", { group, component }));
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <section className="panel finder" aria-label="Public platelet finder">
      <h3>Public platelet finder</h3>
      <p className="small">
        For families and attendants. Shows which blood centres list platelets of a group, and how far their recent
        listings have held up. No login, and nothing about you is stored.
      </p>
      <form className="search" onSubmit={search}>
        <label>
          Blood group
          <select className="field" value={group} onChange={(e) => setGroup(e.target.value)}>
            {GROUPS.map((g) => <option key={g}>{g}</option>)}
          </select>
        </label>
        <label>
          Platelet type
          <select className="field" value={component} onChange={(e) => setComponent(e.target.value)}>
            <option value="RDP">Random donor (RDP)</option>
            <option value="SDP">Single donor / apheresis (SDP)</option>
          </select>
        </label>
        <button className="btn pri" type="submit">Search</button>
      </form>
      {error && <div className="alert">{error}</div>}
      {res && (
        <>
          <p className="callfirst">{res.advice}</p>
          {res.results.length === 0 && <p className="small">No centre lists {res.group} {res.component} right now.</p>}
          {res.results.map((r, i) => (
            <div className="result" key={i}>
              <div>
                <div className="cn">{r.centre_name}</div>
                <div className="ct">{r.area}</div>
              </div>
              <div className="likely">
                <b className={`band ${r.band}`}>{r.band}</b>
                <span>likelihood in stock</span>
              </div>
              <div className="meta">
                Lists {r.listed_compatible} unit(s) · updated {r.updated} · call {r.phone}
              </div>
            </div>
          ))}
          <div className="note">
            <b>What the bands mean.</b> Ranked by listed units and how often this centre's past listings were
            confirmed. {res.band_note} Even “Low” often has stock, and “High” is not a guarantee, so always call first.
          </div>
        </>
      )}
    </section>
  );
}
