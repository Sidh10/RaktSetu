import { useCallback, useEffect, useState } from "react";
import { get, istTime, loadPref, savePref, setUser } from "./api.js";
import Board from "./components/Board.jsx";
import Finder from "./components/Finder.jsx";
import TrustView from "./components/TrustView.jsx";
import AuditView from "./components/AuditView.jsx";
import MyCentre from "./components/MyCentre.jsx";
import Inbox from "./components/Inbox.jsx";
import Toast from "./components/Toast.jsx";
import Home from "./components/Home.jsx";

const PAGES = [
  { id: "board", label: "Coordinator board", roles: ["coordinator", "centre_staff", "medical_officer"] },
  { id: "inbox", label: "Message inbox (mock channel)", roles: ["coordinator", "centre_staff", "medical_officer"] },
  { id: "centre", label: "My centre", roles: ["centre_staff", "medical_officer"] },
  { id: "trust", label: "Report trust", roles: ["coordinator", "medical_officer"] },
  { id: "audit", label: "Audit log", roles: ["coordinator"] },
  { id: "finder", label: "Public platelet finder", roles: ["coordinator", "centre_staff", "medical_officer", "public"] },
  { id: "home", label: "About RaktSetu", roles: ["coordinator", "centre_staff", "medical_officer", "public"] },
];

const ROLE_LABEL = { coordinator: "Coordinator", centre_staff: "Centre staff", medical_officer: "Medical officer" };

function pageFromHash() {
  return window.location.hash.replace("#/", "") || "home";
}

export default function App() {
  const [users, setUsers] = useState([]);
  const [userId, setUserId] = useState(() => loadPref("raktsetu.user", "u-coord"));
  const [page, setPage] = useState(pageFromHash);
  const [health, setHealth] = useState(null);
  const [toast, setToast] = useState(null);

  setUser(userId);
  const user = users.find((u) => u.id === userId) || { id: "", role: "public", display_name: "Public (no login)" };

  useEffect(() => {
    get("/api/demo/users").then(setUsers).catch((e) => setToast({ error: true, title: "API not reachable", text: e.message }));
  }, []);

  useEffect(() => {
    const load = () => get("/api/health").then(setHealth).catch(() => setHealth(null));
    load();
    const id = setInterval(load, 15000);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    const onHash = () => setPage(pageFromHash());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  const allowed = PAGES.filter((p) => p.roles.includes(user.role));
  const current = allowed.find((p) => p.id === page) || allowed[0];

  const go = (id) => {
    window.location.hash = `#/${id}`;
    setPage(id);
  };

  useEffect(() => { window.scrollTo(0, 0); }, [current.id]);

  const chooseUser = (id) => {
    setUserId(id);
    savePref("raktsetu.user", id);
    setUser(id);
  };

  const notify = useCallback((t) => setToast(t), []);

  const labels = (
    <div className="labels" role="note">
      <span><b>Simulated data</b> · <b>mock channel</b> · <b>not clinically validated</b></span>
      <span>Fictional centres and people. Every transfer needs a medical officer's approval.</span>
    </div>
  );

  if (current.id === "home") {
    return (
      <>
        {labels}
        <Home />
        {toast && <Toast {...toast} onClose={() => setToast(null)} />}
      </>
    );
  }

  return (
    <>
      {labels}
      <header className="appbar">
        <div className="row">
          <a className="logo" href="#/home" title="About RaktSetu">
            RaktSetu<span>Platelet bridge · simulated 8-centre city</span>
          </a>
          <div className="who">
            {health && (
              <span className="tag" title="Seeded demo clock: starts at 09:00 IST when the city is seeded (ADR-013)">
                {health.demo_clock ? "Demo clock" : "Clock"} {istTime(health.now)} IST{health.demo_clock ? " (simulated)" : ""}
              </span>
            )}
            <label htmlFor="who">Acting as</label>
            <select id="who" value={userId} onChange={(e) => chooseUser(e.target.value)}>
              <option value="">Public (no login)</option>
              {users.map((u) => (
                <option key={u.id} value={u.id}>
                  {ROLE_LABEL[u.role]} · {u.display_name}
                </option>
              ))}
            </select>
            <span className="tag">Demo users · not real authentication</span>
          </div>
        </div>
        <nav className="nav" aria-label="Pages">
          {allowed.filter((p) => p.id !== "home").map((p) => (
            <button key={p.id} className={p.id === current.id ? "on" : ""} onClick={() => go(p.id)}>
              {p.label}
            </button>
          ))}
        </nav>
      </header>
      <main className="shell">
        {current.id === "board" && <Board key={userId} user={user} users={users} notify={notify} />}
        {current.id === "inbox" && <Inbox key={userId} user={user} notify={notify} />}
        {current.id === "centre" && <MyCentre key={userId} user={user} notify={notify} />}
        {current.id === "trust" && <TrustView key={userId} />}
        {current.id === "audit" && <AuditView key={userId} />}
        {current.id === "finder" && <Finder />}
        <div className="foot">
          Prototype for VIT Code_Apex 3.0, Team Trex. Outcome numbers quoted anywhere come from the v3 simulator and are
          simulated. Matching rules encode DGHS/NBTC 2023 and SNBTS guidance and await specialist review.{" "}
          <a href="#/home">About RaktSetu</a>
        </div>
      </main>
      {toast && <Toast {...toast} onClose={() => setToast(null)} />}
    </>
  );
}
