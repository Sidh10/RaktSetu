import { useEffect, useState } from "react";
import { get, istDateTime } from "../api.js";

export default function AuditView() {
  const [rows, setRows] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    get("/api/audit").then(setRows).catch((e) => setError(e.message));
  }, []);

  if (error) return <div className="alert">{error}</div>;
  if (!rows) return <p className="small">Loading…</p>;
  return (
    <section className="panel" aria-label="Audit log">
      <h3>Audit log (append-only)</h3>
      <div className="table-scroll">
        <table>
          <thead>
            <tr><th>When (IST)</th><th>Who</th><th>Role</th><th>What</th><th>Change</th><th>Note</th></tr>
          </thead>
          <tbody>
            {[...rows].reverse().map((r, i) => (
              <tr key={i}>
                <td className="small">{istDateTime(r.at)}</td>
                <td className="small">{r.actor || "—"}</td>
                <td className="small">{r.role}</td>
                <td>{r.entity} {r.entity_id}</td>
                <td className="small">{r.from_state || "—"} → {r.to_state || r.action}</td>
                <td className="small">{r.note}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
