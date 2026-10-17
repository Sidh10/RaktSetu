import { useState } from "react";
import { post } from "../api.js";
import { errorToast } from "./Toast.jsx";

export default function MatchPanel({ users, notify, lastRun, onRun }) {
  const [policy, setPolicy] = useState("strict");
  const [ack, setAck] = useState("");
  const [busy, setBusy] = useState(false);
  const mos = users.filter((u) => u.role === "medical_officer");

  const run = async () => {
    setBusy(true);
    try {
      const r = await post("/api/match/run", { policy, acknowledged_by: policy === "strict" ? null : ack || null });
      onRun(r);
      notify({ title: `Matcher ran (${policy})`, text: `${r.suggested.length} transfer(s) suggested.` });
    } catch (e) {
      notify(errorToast(e, "Run matcher"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <h3>Run matcher</h3>
      <div className="acts">
        <select className="field" value={policy} onChange={(e) => setPolicy(e.target.value)} aria-label="Matching policy">
          <option value="strict">Strict: ABO/RhD-identical (default)</option>
          <option value="standard">Standard: plasma-compatible ABO</option>
          <option value="relaxed">Relaxed: shortage policy</option>
        </select>
        <button className="btn pri" onClick={run} disabled={busy}>{busy ? "Running…" : "Run"}</button>
      </div>
      {policy !== "strict" && (
        <div className="alert">
          Non-identical matching is not clinically validated and needs a medical officer's acknowledgement.
          <div className="acts">
            <select className="field" value={ack} onChange={(e) => setAck(e.target.value)} aria-label="Acknowledging medical officer">
              <option value="">Choose medical officer…</option>
              {mos.map((m) => <option key={m.id} value={m.id}>{m.display_name}</option>)}
            </select>
          </div>
        </div>
      )}
      {lastRun && (
        <>
          <h4>Last run · {lastRun.policy} · {lastRun.suggested.length} suggested</h4>
          {lastRun.notes.map((n, i) => <div key={i} className="list-item">Note: {n}</div>)}
          {lastRun.unmatched_needs.map((u, i) => (
            <div key={i} className="list-item">Not matched: {u.centre_name} still needs {u.open} × {u.abo_rh} {u.component}. {u.why}.</div>
          ))}
          {lastRun.notes.length === 0 && lastRun.unmatched_needs.length === 0 && (
            <div className="list-item">Every open need was matched.</div>
          )}
        </>
      )}
    </>
  );
}
