import { useCallback, useEffect, useState } from "react";
import { GROUPS, get, istDateTime, patch, post } from "../api.js";
import { errorToast } from "./Toast.jsx";

const FLAG_TEXT = {
  unknown_group: "blood group unclear",
  count_missing: "count missing",
  expiry_missing: "expiry missing",
  expiry_in_past: "expiry date in the past",
  expiry_relative: "relative date resolved: please check",
  component_assumed: "platelet type not stated (RDP assumed)",
  possible_patient_data: "may contain patient data",
  centre_mismatch: "mentions another centre",
  unknown_sender: "sender not recognised",
  no_items: "nothing to record",
};
const BLOCKING = new Set(["unknown_group", "count_missing", "expiry_missing", "expiry_in_past",
  "possible_patient_data", "no_items", "unknown_sender"]);

function Flag({ f }) {
  return <span className={`chip ${BLOCKING.has(f) ? "bad" : "warn"}`}>{FLAG_TEXT[f] || f}</span>;
}

function toEdit(items) {
  return items.map((i) => ({
    abo_rh: i.abo_rh || "", component: i.component || "RDP", count: i.count ?? "",
    expiry_date: (i.expiry && i.expiry.resolved_date) || "", source_span: i.source_span || "",
    flags: i.flags || [],
  }));
}

function DraftCard({ d, notify, onChanged }) {
  const p = d.payload;
  const pending = d.status === "pending";
  const [type, setType] = useState(p.message_type);
  const [mode, setMode] = useState(p.commit_mode || "add");
  const [items, setItems] = useState(toEdit(p.items));
  const [redacted, setRedacted] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [busy, setBusy] = useState(false);

  const setItem = (k, field, value) => {
    setItems(items.map((it, i) => (i === k ? { ...it, [field]: value } : it)));
    setDirty(true);
  };

  const run = async (fn, label) => {
    setBusy(true);
    try {
      const r = await fn();
      if (label) notify({ title: label, text: r && r.kind ? describe(r) : "" });
      onChanged();
    } catch (e) {
      notify(errorToast(e, label || "Inbox"));
    } finally {
      setBusy(false);
    }
  };

  const save = () => run(async () => {
    const r = await patch(`/api/parser/drafts/${d.id}`, {
      message_type: type, commit_mode: mode, patient_data_redacted: redacted,
      items: items.map((i) => ({
        abo_rh: i.abo_rh || null, component: i.component, count: i.count === "" ? null : Number(i.count),
        expiry_date: i.expiry_date || null, source_span: i.source_span,
      })),
    });
    setDirty(false);
    return r;
  }, "Review saved");

  const commit = () => run(() => post(`/api/parser/drafts/${d.id}/commit`), "Committed");
  const discard = () => {
    const reason = window.prompt("Reason for discarding?");
    if (reason) run(() => post(`/api/parser/drafts/${d.id}/discard`, { reason }), "Discarded");
  };

  return (
    <article className={`card ${pending ? "" : "done"}`} aria-label={`Draft ${d.id}`}>
      <div className="route">
        <b>Draft #{d.id}</b>
        <span className="small">{d.channel.replace("_", " ")} · from {d.sender} · {istDateTime(d.received_at)}</span>
        <span className="qty">{d.status}</span>
      </div>
      <div className="msg">{d.text}</div>
      <div className="chips">
        <span className="chip">{d.parser === "llm" ? `Parsed by LLM (${d.model})` : "Parsed by rules"} · human check required</span>
        <span className="chip">mock channel</span>
        {p.message_flags.map((f) => <Flag key={f} f={f} />)}
      </div>
      {p.notes.map((n, i) => <div key={i} className="small">• {n}</div>)}

      {pending && (
        <div className="acts">
          <label className="check">Type
            <select className="field" value={type} onChange={(e) => { setType(e.target.value); setDirty(true); }}>
              <option value="stock_post">Stock post</option>
              <option value="shortfall">Shortfall request</option>
              <option value="other">Other (nothing to record)</option>
            </select>
          </label>
          {type === "stock_post" && (
            <label className="check" title="Add keeps the rest of the listing; replace treats the message as the full stock list">Commit as
              <select className="field" value={mode} onChange={(e) => { setMode(e.target.value); setDirty(true); }}>
                <option value="add">add to listing</option>
                <option value="replace">replace whole listing</option>
              </select>
            </label>
          )}
        </div>
      )}

      {items.length > 0 && (
        <div className="table-scroll">
          <table>
            <thead><tr><th>Group</th><th>Type</th><th>Count</th>{type === "stock_post" && <th>Expires on</th>}<th>Checks</th></tr></thead>
            <tbody>
              {items.map((it, k) => (
                <tr key={k}>
                  <td>
                    <select className="field" disabled={!pending} value={it.abo_rh} aria-label="Group"
                      onChange={(e) => setItem(k, "abo_rh", e.target.value)}>
                      <option value="">?</option>
                      {GROUPS.map((g) => <option key={g}>{g}</option>)}
                    </select>
                  </td>
                  <td>
                    <select className="field" disabled={!pending} value={it.component} aria-label="Platelet type"
                      onChange={(e) => setItem(k, "component", e.target.value)}>
                      <option>RDP</option><option>SDP</option>
                    </select>
                  </td>
                  <td><input type="number" min="0" max="50" disabled={!pending} value={it.count} aria-label="Count"
                    onChange={(e) => setItem(k, "count", e.target.value)} /></td>
                  {type === "stock_post" && (
                    <td><input type="date" className="field" disabled={!pending} value={it.expiry_date} aria-label="Expiry date"
                      onChange={(e) => setItem(k, "expiry_date", e.target.value)} /></td>
                  )}
                  <td>{dirty ? <span className="small">save to re-check</span> : it.flags.map((f) => <Flag key={f} f={f} />)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {pending && (
        <>
          {p.message_flags.includes("possible_patient_data") && (
            <label className="check">
              <input type="checkbox" checked={redacted} onChange={(e) => { setRedacted(e.target.checked); setDirty(true); }} />
              Remove the raw text (may contain patient data); keep only the fields above
            </label>
          )}
          <div className="acts">
            <button className="btn" disabled={busy || !dirty} onClick={save}>Save review</button>
            <button className="btn pri" disabled={busy || dirty || d.blocking.length > 0} onClick={commit}
              aria-describedby={`why-${d.id}`}>
              Commit
            </button>
            <button className="btn" disabled={busy} onClick={discard}>Discard</button>
            <span id={`why-${d.id}`} className="wait">
              {dirty ? "Save the review first." : d.blocking.length > 0 ? `Fix first: ${d.blocking.map((f) => FLAG_TEXT[f] || f).join(", ")}.` : "Ready to commit."}
            </span>
          </div>
        </>
      )}
    </article>
  );
}

function describe(r) {
  if (r.kind === "shortfall") return `${r.shortfall_ids.length} shortfall request(s) created.`;
  return r.mode === "replace"
    ? `Listing replaced: ${r.listed} unit(s) listed, ${r.superseded} superseded.`
    : `${r.listed} unit(s) added to the listing (listing age unchanged).`;
}

export default function Inbox({ user, notify }) {
  const isCoord = user.role === "coordinator";
  const [text, setText] = useState("");
  const [channel, setChannel] = useState("mock_whatsapp");
  const [centre, setCentre] = useState(user.centre_id || "C-H");
  const [centres, setCentres] = useState([]);
  const [samples, setSamples] = useState([]);
  const [drafts, setDrafts] = useState([]);
  const [showDone, setShowDone] = useState(false);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      setDrafts(await get("/api/parser/drafts"));
    } catch (e) {
      notify(errorToast(e, "Load inbox"));
    }
  }, [notify]);

  useEffect(() => {
    load();
    get("/api/channel/samples").then((s) => setSamples(s.samples)).catch(() => {});
    get("/api/centres").then(setCentres).catch(() => {});
  }, [load]);

  const send = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      const r = await post("/api/channel/mock/inbound", { channel, text, centre_id: isCoord ? centre : null });
      notify({ title: `Draft #${r.parse_draft_id} created`, text: r.needs_review.length ? `Needs review: ${r.needs_review.map((f) => FLAG_TEXT[f] || f).join(", ")}.` : "No flags; still check it before committing." });
      setText("");
      load();
    } catch (err) {
      notify(errorToast(err, "Send message"));
    } finally {
      setBusy(false);
    }
  };

  const mySamples = samples.filter((s) => isCoord || s.centre === user.centre_id);
  const pending = drafts.filter((d) => d.status === "pending");
  const done = drafts.filter((d) => d.status !== "pending");

  return (
    <div className="grid inbox">
      <section className="panel" aria-label="Paste a message">
        <h3>Paste a stock message</h3>
        <div className="alert">
          <b>Mock channel.</b> Nothing is received from WhatsApp or SMS. Type or paste a message as a centre would send it;
          it becomes a draft that a person must check before any stock changes.
        </div>
        <form onSubmit={send}>
          <div className="acts">
            <select className="field" value={channel} onChange={(e) => setChannel(e.target.value)} aria-label="Channel">
              <option value="mock_whatsapp">mock WhatsApp</option>
              <option value="mock_sms">mock SMS</option>
              <option value="paste">paste</option>
            </select>
            {isCoord ? (
              <select className="field" value={centre} onChange={(e) => setCentre(e.target.value)} aria-label="Sending centre">
                {centres.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            ) : (
              <span className="small">from your centre ({user.centre_id})</span>
            )}
          </div>
          <textarea className="field area" rows={4} value={text} onChange={(e) => setText(e.target.value)}
            placeholder="e.g. O+ RDP 2 unit kal expire, B+ 1" aria-label="Message text" />
          <div className="acts">
            <button className="btn pri" type="submit" disabled={busy || !text.trim()}>Parse into a draft</button>
          </div>
        </form>
        {mySamples.length > 0 && (
          <>
            <h4>Sample messages (synthetic)</h4>
            {mySamples.map((s, i) => (
              <button key={i} className="btn sample" onClick={() => { setText(s.text); setChannel(s.channel); if (isCoord) setCentre(s.centre); }}>
                {s.centre} · {s.text}
              </button>
            ))}
          </>
        )}
        <div className="note">English and Hinglish (Latin script) are supported. Hindi and Marathi are planned. Parsing
          uses the Claude API when a key is configured, otherwise the offline rule-based parser; both drafts get the same checks.</div>
      </section>
      <section className="panel" aria-label="Drafts">
        <h3>Drafts awaiting a human check ({pending.length})</h3>
        {pending.length === 0 && <p className="small">No drafts waiting.</p>}
        {pending.map((d) => <DraftCard key={`${d.id}-${d.status}-${d.payload.needs_review.join()}`} d={d} notify={notify} onChanged={load} />)}
        {done.length > 0 && (
          <>
            <button className="btn link" onClick={() => setShowDone(!showDone)}>{showDone ? "Hide" : "Show"} committed and discarded ({done.length})</button>
            {showDone && done.map((d) => <DraftCard key={d.id} d={d} notify={notify} onChanged={load} />)}
          </>
        )}
      </section>
    </div>
  );
}
