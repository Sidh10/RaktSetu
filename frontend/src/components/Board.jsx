import { useCallback, useEffect, useState } from "react";
import { get } from "../api.js";
import TransferCard from "./TransferCard.jsx";
import MatchPanel from "./MatchPanel.jsx";

const TERMINAL = ["failed", "delivered", "cancelled"];

function Band({ band }) {
  return (
    <>
      <div className="tb">
        <div className={`bar ${band}`} />
      </div>
      <span className={`band ${band}`}>{band}</span>
    </>
  );
}

export default function Board({ user, users, notify }) {
  const [board, setBoard] = useState(null);
  const [transfers, setTransfers] = useState([]);
  const [lastRun, setLastRun] = useState(null);
  const [showDone, setShowDone] = useState(false);

  const load = useCallback(async () => {
    try {
      const [b, t] = await Promise.all([get("/api/board"), get("/api/transfers")]);
      setBoard(b);
      setTransfers(t);
    } catch (e) {
      notify({ error: true, title: "Could not load the board", text: e.message });
    }
  }, [notify]);

  useEffect(() => {
    load();
    const id = setInterval(load, 10000);
    return () => clearInterval(id);
  }, [load]);

  if (!board) return <p className="small">Loading board…</p>;
  const k = board.kpis;
  const open = transfers.filter((t) => !TERMINAL.includes(t.status));
  const done = transfers.filter((t) => TERMINAL.includes(t.status)).reverse();
  const isCoord = user.role === "coordinator";

  return (
    <>
      <div className="kpis">
        <div className="kpi"><div className="v">{k.near_expiry_listed}</div><div className="l">platelet units listed as expiring within 2 days</div></div>
        <div className="kpi"><div className="v">{k.transfers_awaiting_action}</div><div className="l">transfers awaiting action</div></div>
        <div className="kpi"><div className="v">{k.centres_fresh_24h}/{board.centres.length}</div><div className="l">centres with stock data under 24 h old</div></div>
        <div className="kpi"><div className="v">{k.delivered_7d}</div><div className="l">transfers delivered in the last 7 days</div></div>
      </div>
      <div className="grid">
        <section className="panel" aria-label="Centre stock and report trust">
          <h3>Centre stock and report trust</h3>
          <div className="table-scroll">
            <table>
              <thead>
                <tr><th>Centre</th><th>Listed</th><th>≤ 2 days</th><th>Last update</th><th>Report trust</th></tr>
              </thead>
              <tbody>
                {board.centres.map((c) => (
                  <tr key={c.id} className={c.id === user.centre_id ? "mine" : ""}>
                    <td>
                      <div className="cn">{c.name}</div>
                      <div className="ct">
                        {c.kind === "hospital" ? "Hospital" : "Collection"}
                        {c.received > 0 && ` · ${c.received} received (never re-offered)`}
                        {Object.keys(c.offerable).length > 0 &&
                          ` · offers ${Object.entries(c.offerable).map(([g, n]) => `${n} × ${g}`).join(", ")}`}
                      </div>
                    </td>
                    <td className="num">{c.listed}</td>
                    <td className="num">{c.near_expiry}</td>
                    <td className={c.listing_age_bucket > 0 ? "stale" : ""}>{c.updated}</td>
                    <td><Band band={c.trust_band} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="note">
            Report trust: a band learned from past confirmations, estimated separately for listings updated today,
            1 day ago and 2+ days ago (Beta(2,1) prior). Low &lt; 0.5 ≤ Medium &lt; 0.8 ≤ High. Seeded history is
            simulated.
          </div>
        </section>

        <section className="panel" aria-label="Transfers">
          <h3>Transfers (a medical officer approves each)</h3>
          {open.length === 0 && (
            <p className="small">{isCoord ? "No open transfers. Run the matcher to get suggestions." : "No open transfers for your centre."}</p>
          )}
          {open.map((t) => (
            <TransferCard key={t.id} t={t} user={user} notify={notify} onChanged={load} />
          ))}
          {done.length > 0 && (
            <>
              <button className="btn link" onClick={() => setShowDone(!showDone)}>
                {showDone ? "Hide" : "Show"} finished transfers ({done.length})
              </button>
              {showDone && done.map((t) => <TransferCard key={t.id} t={t} user={user} notify={notify} onChanged={load} />)}
            </>
          )}
        </section>

        <section className="panel" aria-label="Matcher">
          {isCoord ? (
            <MatchPanel users={users} notify={notify} lastRun={lastRun}
              onRun={(r) => { setLastRun(r); load(); }} />
          ) : (
            <>
              <h3>Your role</h3>
              <p className="small">
                {user.role === "medical_officer"
                  ? "You approve or reject confirmed transfers sent from your centre, and you can confirm and dispatch."
                  : "You confirm how many units your centre really has, dispatch approved transfers and mark arrivals."}
              </p>
            </>
          )}
          <h4>How a transfer moves</h4>
          <ol className="small" style={{ paddingLeft: 18, margin: 0 }}>
            <li>Matcher suggests (strict ABO/RhD, one-hop, near-expiry surplus only)</li>
            <li>Coordinator asks the sending centre to confirm</li>
            <li>Sending centre reports units actually there</li>
            <li>Medical officer approves (12-h margin re-checked)</li>
            <li>Dispatch, then the receiving centre marks delivered</li>
          </ol>
          <div className="note">
            The 12-hour margin on arrival is a safety margin chosen by the team, not a regulation. Transport times are
            seeded estimates.
          </div>
        </section>
      </div>
    </>
  );
}
