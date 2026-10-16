import { useCallback, useEffect, useState } from "react";
import { GROUPS, get, istDateTime, post } from "../api.js";
import { errorToast } from "./Toast.jsx";

export default function MyCentre({ user, notify }) {
  const [units, setUnits] = useState([]);
  const [shortfalls, setShortfalls] = useState([]);
  const [form, setForm] = useState({ abo_rh: "O+", component: "RDP", count: 1, identical_only: false });

  const load = useCallback(async () => {
    try {
      const [u, s] = await Promise.all([get(`/api/centres/${user.centre_id}/units`), get("/api/shortfalls")]);
      setUnits(u);
      setShortfalls(s);
    } catch (e) {
      notify(errorToast(e, "Load centre"));
    }
  }, [user.centre_id, notify]);

  useEffect(() => { load(); }, [load]);

  const submit = async (e) => {
    e.preventDefault();
    try {
      await post("/api/shortfalls", { ...form, count: Number(form.count) });
      notify({ title: "Shortfall posted", text: `${form.count} × ${form.abo_rh} ${form.component}. The coordinator's next matcher run will look for it.` });
      load();
    } catch (err) {
      notify(errorToast(err, "Post shortfall"));
    }
  };

  return (
    <div className="grid">
      <section className="panel" aria-label="Listed units">
        <h3>Units your centre lists ({units.length})</h3>
        <div className="table-scroll">
          <table>
            <thead><tr><th>Unit ID</th><th>Group</th><th>Type</th><th>Expires (IST)</th><th>Hours left</th><th></th></tr></thead>
            <tbody>
              {units.map((u) => (
                <tr key={u.id}>
                  <td className="small">{u.id}</td>
                  <td>{u.abo_rh}</td>
                  <td>{u.component}</td>
                  <td className="small">{istDateTime(u.expires_at)}</td>
                  <td className={`num ${u.days_left <= 2 ? "stale" : ""}`}>{u.hours_left}</td>
                  <td className="small">{u.received_via_transfer ? "received: not re-offered" : ""}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="note">Unit IDs are random platform IDs, not bag numbers, so they cannot be linked to donors.
          Stock is posted by message (mock channel) or form; message parsing arrives in Stage 4.</div>
      </section>
      <section className="panel" aria-label="Shortfalls">
        <h3>Post a shortfall</h3>
        <form className="acts" onSubmit={submit}>
          <select className="field" value={form.abo_rh} onChange={(e) => setForm({ ...form, abo_rh: e.target.value })} aria-label="Group">
            {GROUPS.map((g) => <option key={g}>{g}</option>)}
          </select>
          <select className="field" value={form.component} onChange={(e) => setForm({ ...form, component: e.target.value })} aria-label="Type">
            <option>RDP</option><option>SDP</option>
          </select>
          <input type="number" min="1" max="50" value={form.count} aria-label="Units needed"
            onChange={(e) => setForm({ ...form, count: e.target.value })} />
          <label className="check">
            <input type="checkbox" checked={form.identical_only} onChange={(e) => setForm({ ...form, identical_only: e.target.checked })} />
            ABO-identical only (e.g. infant)
          </label>
          <button className="btn pri" type="submit">Post</button>
        </form>
        <div className="note">Group, type and count only. Never enter patient details.</div>
        <h4>Your shortfalls</h4>
        {shortfalls.length === 0 && <p className="small">None.</p>}
        {shortfalls.map((s) => (
          <div key={s.id} className="list-item">
            #{s.id} · {s.count_requested} × {s.abo_rh} {s.component}{s.identical_only ? " (identical only)" : ""} ·
            {" "}{s.count_open} open · {s.status}
          </div>
        ))}
      </section>
    </div>
  );
}
