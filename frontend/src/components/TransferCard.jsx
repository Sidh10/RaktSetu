import { useState } from "react";
import { get, istDateTime, post } from "../api.js";
import { errorToast } from "./Toast.jsx";

const STATUS = {
  suggested: "Suggested",
  confirm_requested: "Awaiting sending-centre confirmation",
  confirmed: "Confirmed · awaiting medical officer",
  approved: "Approved · ready to dispatch",
  dispatched: "In transit",
  delivered: "Delivered",
  failed: "Failed: no usable units found",
  cancelled: "Cancelled",
};

const short = (name) => name.split(" · ")[0];

export default function TransferCard({ t, user, notify, onChanged }) {
  const [busy, setBusy] = useState(false);
  const [found, setFound] = useState(t.qty_requested);
  const [box, setBox] = useState(false);
  const [history, setHistory] = useState(null);

  const isCoord = user.role === "coordinator";
  const isSender = user.centre_id === t.from_centre;
  const isReceiver = user.centre_id === t.to_centre;
  const isMO = user.role === "medical_officer";
  const terminal = ["failed", "delivered", "cancelled"].includes(t.status);

  const act = async (action, body, label) => {
    setBusy(true);
    try {
      const r = await post(`/api/transfers/${t.id}/${action}`, body);
      const tr = r.result && r.result.trust;
      notify({
        title: `${label}: ${STATUS[r.status]}`,
        text: tr ? `Report trust for ${short(t.from_name)} (listings ${["today", "1 day old", "2+ days old"][tr.bucket]}): α ${tr.alpha}, β ${tr.beta}, band ${tr.band_before} → ${tr.band_after}.` : "",
      });
      if (history) setHistory(null);
      onChanged();
    } catch (e) {
      notify(errorToast(e, label));
    } finally {
      setBusy(false);
    }
  };

  const withReason = (action, label, question) => {
    const reason = window.prompt(question);
    if (reason) act(action, { reason }, label);
  };

  const toggleHistory = async () => {
    if (history) return setHistory(null);
    try {
      setHistory((await get(`/api/transfers/${t.id}`)).audit);
    } catch (e) {
      notify(errorToast(e, "History"));
    }
  };

  const minHours = t.units.length ? Math.min(...t.units.map((u) => u.hours_left_on_arrival)) : null;
  const qty = t.qty_confirmed ?? t.qty_requested;

  return (
    <article className={`card ${terminal ? "done" : ""}`} aria-label={`Transfer ${t.id}`}>
      <div className="route">
        <b>{short(t.from_name)}</b><span className="arrow">→</span><b>{short(t.to_name)}</b>
        <span className="qty">{qty} × {t.abo_rh_offered} {t.component}</span>
      </div>
      <span className={`status ${t.status}`}>#{t.id} · {STATUS[t.status]}</span>
      <div className="why">Why: {t.reason}</div>
      <div className="chips">
        <span className={`chip ${t.sender_band}`}>Sender trust {t.sender_band}</span>
        <span className="chip">{t.tier === 0 ? "ABO/RhD identical" : `Non-identical · ${t.policy} policy`}</span>
        {t.anti_d_flag && <span className="chip bad">Anti-D consideration</span>}
        <span className="chip">One-hop rule met</span>
        {minHours !== null ? (
          <span className={`chip ${minHours >= 12 ? "" : "bad"}`}>
            {minHours >= 12 ? "≥ 12 h on arrival" : "< 12 h on arrival"} (min {minHours} h)
          </span>
        ) : (
          <span className="chip">Transport estimate {t.transport_min} min</span>
        )}
        {t.box_validated !== null && t.box_validated !== undefined && (
          <span className={`chip ${t.box_validated ? "" : "warn"}`}>20–24 °C box {t.box_validated ? "recorded" : "not confirmed"} (not verified)</span>
        )}
      </div>

      {!terminal && (
        <div className="acts">
          {t.status === "suggested" && isCoord && (
            <button className="btn pri" disabled={busy} onClick={() => act("request-confirmation", {}, "Request confirmation")}>
              Request confirmation
            </button>
          )}
          {t.status === "confirm_requested" && isSender && (
            <>
              <label className="check">
                Units actually available
                <input type="number" min="0" max={t.qty_requested} value={found}
                  onChange={(e) => setFound(Number(e.target.value))} />
                of {t.qty_requested}
              </label>
              <button className="btn pri" disabled={busy} onClick={() => act("confirm", { units_available: found }, "Confirm")}>
                Confirm
              </button>
            </>
          )}
          {t.status === "confirm_requested" && !isSender && (
            <span className="wait">Waiting for {short(t.from_name)} to confirm the units are there.</span>
          )}
          {t.status === "confirmed" && isSender && (
            <>
              <button className="btn pri" disabled={busy} onClick={() => act("approve", {}, "Approve")}>
                Approve dispatch
              </button>
              {isMO && (
                <button className="btn" disabled={busy} onClick={() => withReason("reject", "Reject", "Reason for rejecting?")}>
                  Reject
                </button>
              )}
            </>
          )}
          {t.status === "confirmed" && !isSender && <span className="wait">Waiting for the medical officer at {short(t.from_name)}.</span>}
          {t.status === "approved" && isSender && (
            <>
              <label className="check">
                <input type="checkbox" checked={box} onChange={(e) => setBox(e.target.checked)} />
                Validated 20–24 °C transport box used
              </label>
              <button className="btn pri" disabled={busy} onClick={() => act("dispatch", { box_validated: box }, "Dispatch")}>
                Dispatch
              </button>
            </>
          )}
          {t.status === "approved" && !isSender && <span className="wait">Approved; {short(t.from_name)} will dispatch.</span>}
          {t.status === "dispatched" && isReceiver && (
            <button className="btn pri" disabled={busy} onClick={() => act("deliver", {}, "Mark delivered")}>Mark delivered</button>
          )}
          {t.status === "dispatched" && !isReceiver && <span className="wait">In transit to {short(t.to_name)}.</span>}
          {isCoord && (
            <button className="btn" disabled={busy}
              onClick={() => withReason("cancel", "Cancel", t.status === "dispatched" ? "Reason (lost or damaged in transit?)" : "Reason for cancelling?")}>
              Cancel
            </button>
          )}
        </div>
      )}
      <div className="acts">
        <button className="btn link" onClick={toggleHistory}>{history ? "Hide history" : "History"}</button>
      </div>
      {history && (
        <div className="history">
          {history.map((h, i) => (
            <div key={i}>
              {istDateTime(h.at)} · {h.role}{h.actor ? ` (${h.actor})` : ""}: {h.from_state || "—"} → {h.to_state}
              {h.note ? ` · ${h.note}` : ""}
            </div>
          ))}
        </div>
      )}
    </article>
  );
}
