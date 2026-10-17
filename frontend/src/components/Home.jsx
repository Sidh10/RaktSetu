import { useEffect, useRef, useState } from "react";
import { GROUPS, get } from "../api.js";

// Public front page. Bands only, never a number per centre (docs/CLAIMS_AND_LIMITS.md section 5).
// The example transfer in "How a unit crosses" is the first suggestion of the seeded demo city (simulated).
const RANK = { High: 3, Medium: 2, Low: 1 };

const STEPS = [
  { field: "maroon", clause: "First the matcher finds a unit that would expire unused.",
    status: "Suggested", chips: [["High", "Sender trust High"], ["", "ABO/RhD identical"]] },
  { field: "mustard", clause: "Then the sending centre counts it: is it really there?",
    status: "Confirmed · 2 of 2 there", chips: [["", "Awaiting medical officer"]] },
  { field: "slate", clause: "Then a medical officer approves, or nothing moves.",
    status: "Approved · ready to dispatch", chips: [["", "≥ 12 h on arrival (min 13.5 h)"]] },
  { field: "red", clause: "Then it travels, with at least 12 hours to spare.",
    status: "Delivered", chips: [["", "20–24 °C box recorded"]] },
];

const RULES = [
  ["same group", "ABO and RhD identical by default"],
  ["two days left", "offered only if it would expire unused"],
  ["twelve hours", "left on arrival, checked twice"],
  ["confirm first", "units counted before anyone travels"],
  ["officer signs", "a medical officer approves each one"],
  ["one hop", "a received unit is never re-offered"],
];

const FAQ = [
  ["Is this real stock?",
    "No. This prototype runs on simulated data: the eight centres, their stock and their phone numbers are fictional. Do not use it to look for platelets today."],
  ["What do High, Medium and Low mean?",
    "How likely a centre has the units now, judged from how many it lists and how often its past listings held up when another centre checked. High is not a guarantee, and Low often still has stock."],
  ["Why a band and not a number?",
    "A precise figure would look more certain than a stock listing can be. Three bands say what a listing can honestly tell you, and every answer ends the same way: call before travelling."],
  ["Do I need to log in? Is anything stored?",
    "No login. You choose a blood group and a platelet type, and that is all the finder sees. Nothing about you or the patient is stored."],
  ["What are RDP and SDP?",
    "Random donor platelets (RDP) are separated from whole-blood donations; single donor platelets (SDP) come from one donor by apheresis. The treating doctor says which one the patient needs."],
  ["Who decides that a unit moves?",
    "A medical officer at the sending centre approves every transfer. The software only suggests; people count, approve and carry."],
  ["Why the 12-hour margin?",
    "So a unit never arrives with too little life left to use. It is a margin our team chose, not a regulation, and it is checked again at approval and at dispatch."],
  ["Can centres send stock on WhatsApp?",
    "Not yet. The prototype uses a mock channel: a typed message is read the way a WhatsApp message would be, and a person checks every draft before stock changes."],
  ["Is this clinically validated?",
    "No. The matching rules encode DGHS/NBTC 2023 and SNBTS guidance and are waiting for review by a transfusion specialist. Outcome figures from our simulator are simulated, not measured."],
];

// Fictional city: dot positions by area (data/seed/demo_city.json areas).
const DOTS = [
  ["A", 118, 52], ["G", 150, 70], ["B", 214, 112], ["C", 128, 118], ["F", 150, 134],
  ["D", 52, 124], ["E", 124, 188], ["H", 236, 196],
];

function MiniCard({ step }) {
  return (
    <div className="mini" data-ui aria-hidden="true">
      <div className="card">
        <div className="route">
          <b>Centre F</b><span className="arrow">→</span><b>Centre C</b>
          <span className="qty">2 × O+ RDP</span>
        </div>
        <span className={`status ${step.status === "Delivered" ? "delivered" : ""}`}>{step.status}</span>
        <div className="chips">
          {step.chips.map(([c, t]) => <span key={t} className={`chip ${c}`}>{t}</span>)}
        </div>
      </div>
    </div>
  );
}

export default function Home() {
  const root = useRef(null);
  const [field, setField] = useState("red");
  const [group, setGroup] = useState("O+");
  const [component, setComponent] = useState("RDP");
  const [res, setRes] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let live = true;
    setError("");
    get("/api/public/finder", { group, component })
      .then((r) => live && setRes(r))
      .catch((e) => live && setError(e.message));
    return () => { live = false; };
  }, [group, component]);

  // The pinned bar takes the colour of the chapter beneath it.
  useEffect(() => {
    let frame = 0;
    const update = () => {
      frame = 0;
      const chapters = root.current ? root.current.querySelectorAll("[data-field]") : [];
      for (const el of chapters) {
        const r = el.getBoundingClientRect();
        if (r.top <= 65 && r.bottom > 65) { setField(el.dataset.field); return; }
      }
    };
    const onScroll = () => { if (!frame) frame = requestAnimationFrame(update); };
    update();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => { window.removeEventListener("scroll", onScroll); cancelAnimationFrame(frame); };
  }, []);

  // Entrances: each part of a section rises in turn, once. Without the observer nothing is hidden.
  useEffect(() => {
    const el = root.current;
    if (!el || !("IntersectionObserver" in window)) return undefined;
    const io = new IntersectionObserver((entries) => {
      entries.forEach((e) => {
        if (!e.isIntersecting) return;
        e.target.classList.add("in");
        io.unobserve(e.target);
      });
    }, { rootMargin: "0px 0px -8% 0px" });
    el.querySelectorAll("[data-reveal]").forEach((n, i) => {
      n.style.transitionDelay = `${(Number(n.dataset.reveal) || 0) * 80}ms`;
      io.observe(n);
    });
    el.classList.add("motion");
    return () => io.disconnect();
  }, []);

  const toFinder = () => document.getElementById("find").scrollIntoView({ behavior: "smooth", block: "start" });
  const best = res && res.results.length
    ? res.results.reduce((a, r) => (RANK[r.band] > RANK[a] ? r.band : a), "Low") : "";

  return (
    <div className="home" ref={root}>
      <header className="hbar" data-field={field}>
        <a className="logo" href="#/home">RaktSetu</a>
        <nav aria-label="Front page">
          <a className="hide-s" href="#/board">For blood centres</a>
          <button className="button small" onClick={toFinder}>Find platelets</button>
        </nav>
      </header>

      <section className="hero f-red" data-field="red">
        <h1 aria-label="RaktSetu"><span className="pale">Rakt</span><span className="dark">Setu</span></h1>
        <div className="hero-foot">
          <h2 className="gloss"><span className="pale">Rakt is blood.</span> <span className="dark">Setu is a bridge.</span></h2>
          <div className="right">
            <p className="line">Platelets keep for five days. RaktSetu moves a unit about to expire to the centre that needs it, and tells families where to call first.</p>
            <div className="go">
              <button className="button ink" onClick={toFinder}>Find platelets</button>
              <a className="text" href="#/board">Open the coordinator board</a>
            </div>
          </div>
        </div>
      </section>

      <section id="find" className="chapter f-bone" data-field="bone" aria-labelledby="find-h">
        <div className="find">
          <div className="pick">
            <h2 id="find-h" data-reveal="0">Find platelets</h2>
            <ul className="groups" aria-label="Blood group">
              {GROUPS.map((g) => (
                <li key={g}>
                  <button aria-pressed={g === group} onClick={() => setGroup(g)}>{g}</button>
                </li>
              ))}
            </ul>
            <div className="kind" role="group" aria-label="Platelet type">
              <button aria-pressed={component === "RDP"} onClick={() => setComponent("RDP")}>Random donor (RDP)</button>
              <button aria-pressed={component === "SDP"} onClick={() => setComponent("SDP")}>Single donor (SDP)</button>
            </div>
            <p className="private">No login, and nothing about you or the patient is stored. Simulated data: the centres and phone numbers are fictional. The disc takes the colour of the best band.</p>
          </div>

          <div className="disc-wrap" data-reveal="1">
            <div className="disc" data-band={best} />
            <div className="bag">
              <img src="/img/platelet-bag.jpg" width="760" height="1029"
                alt="A bag of platelets collected by apheresis: a flat plastic bag of straw-yellow liquid" />
            </div>
          </div>

          <div className="answers" aria-live="polite">
            {error && <div className="alert">{error}</div>}
            {res && (
              <>
                <p className="advice">{res.advice}</p>
                {res.results.length === 0 && <p>No centre lists {res.group} {res.component} right now. Try another type, or call the nearest centre.</p>}
                <ol key={`${group}-${component}`}>
                  {res.results.slice(0, 4).map((r) => (
                    <li key={r.centre_name}>
                      <b>{r.centre_name.split(" · ")[0]}</b>
                      <span className={`band ${r.band}`}>{r.band}</span>
                      <span className="meta">{r.area} · lists {r.listed_compatible} · updated {r.updated} · call {r.phone}</span>
                    </li>
                  ))}
                </ol>
                {res.results.length > 4 && <p className="more">{res.results.length - 4} more on the <a href="#/finder">full finder page</a>.</p>}
              </>
            )}
          </div>
        </div>
      </section>

      <section className="strip" aria-labelledby="how-h">
        {STEPS.map((s, i) => (
          <div key={s.field} className={`f-${s.field}`} data-field={s.field}>
            {i === 0 ? <h2 id="how-h" data-reveal="0">How a unit crosses</h2> : <span />}
            <div className="slot" data-reveal="1"><MiniCard step={s} /></div>
            <p className="clause" data-reveal="2">{s.clause}</p>
          </div>
        ))}
      </section>

      <section className="chapter f-mustard" data-field="mustard" aria-label="The rules every transfer keeps">
        <ul className="rules">
          {RULES.map(([w, f], i) => (
            <li key={w} data-reveal={i % 3}><span className="w">{w}</span><span className="fact">{f}</span></li>
          ))}
        </ul>
      </section>

      <section className="chapter f-slate" data-field="slate" aria-labelledby="why-h">
        <div className="why-ch">
          <figure data-reveal="1">
            <div className="frame">
              <img src="/img/ambulance.jpg" width="1400" height="1050" loading="lazy"
                alt="An advanced life support ambulance in red and yellow livery parked in an Indian building's car park" />
            </div>
            <figcaption>An ambulance in India: the city's roads are where a margin of hours is spent. Photograph by Oleg Yunakov, CC BY-SA 4.0.</figcaption>
          </figure>
          <div className="text">
            <h2 id="why-h" data-reveal="0">Five days to cross</h2>
            <p className="statement" data-reveal="1">A platelet unit lasts five days at 20–24 °C. A spare unit in one centre may be what a patient across town needs.</p>
            <p data-reveal="2">RaktSetu only offers a centre's near-expiry surplus: units due to expire within two days that its own expected use will not reach.</p>
          </div>
        </div>
      </section>

      <section className="chapter f-bone" data-field="bone" aria-labelledby="faq-h">
        <div className="faq">
          <div className="side">
            <h2 id="faq-h" data-reveal="0">Questions families ask</h2>
            <img src="/img/platelets-smear.jpg" width="1100" height="825" loading="lazy" data-reveal="1"
              alt="A stained blood smear under a microscope: a white cell at the centre, red cells around it, platelets as small dark dots" />
            <p>Platelets are the small dark dots among the red cells. Micrograph by Ajay Kumar Chaurasiya, CC BY-SA 4.0.</p>
          </div>
          <div className="tiles">
            {FAQ.map(([q, a], i) => (
              <details key={q} name="faq" open={i === 0}>
                <summary>{q}</summary>
                <p>{a}</p>
              </details>
            ))}
          </div>
        </div>
      </section>

      <section className="chapter f-maroon centres" data-field="maroon" aria-labelledby="ctr-h">
        <h2 id="ctr-h" data-reveal="0">For blood centres</h2>
        <p className="lead" data-reveal="1">One board for the coordinator, one inbox for stock messages, and one button only a medical officer can press. It all runs on a simulated city of eight centres.</p>
        <div className="tiles">
          <div className="shot" data-reveal="1">
            <img src="/img/board.jpg" width="1600" height="1000" loading="lazy"
              alt="The coordinator board: centre stock with report-trust bands, two suggested transfers and the matcher panel" />
            <div className="over">
              <p>The board after a strict matcher run: two transfers suggested, each waiting for the sending centre to confirm.</p>
              Screenshot of this prototype, simulated data.
            </div>
          </div>
          <div className="city" data-reveal="2">
            <div className="map">
              <svg viewBox="0 0 280 240" role="img" aria-label="Map of the fictional city with eight centres, A to H">
                <path d="M40 60 Q60 18 130 22 Q210 20 238 70 Q262 120 252 178 Q240 226 170 222 Q96 228 56 196 Q14 160 22 112 Q26 80 40 60 Z" fill="#952625" />
                {DOTS.map(([l, x, y]) => (
                  <g key={l}>
                    <circle cx={x} cy={y} r="7" fill="#e2dccf" />
                    <text x={x + 11} y={y + 5} fill="#e2dccf" fontSize="15" fontWeight="800" fontFamily="inherit">{l}</text>
                  </g>
                ))}
              </svg>
            </div>
            <dl className="facts">
              <div><dt>Centres</dt><dd>8, fictional</dd></div>
              <div><dt>Roles</dt><dd>3 + public</dd></div>
              <div><dt>Margin</dt><dd>12 h on arrival</dd></div>
              <div><dt>Demo clock</dt><dd>from 09:00 IST</dd></div>
            </dl>
          </div>
        </div>
        <div className="go">
          <a className="button" href="#/board">Open the coordinator board</a>
          <a className="text" href="#/inbox">Message inbox (mock channel)</a>
        </div>
      </section>

      <footer className="close f-red" data-field="red">
        <div className="blocks" aria-label="RaktSetu">
          {"RAKTSETU".split("").map((c, i) => <span key={i} aria-hidden="true">{c}</span>)}
        </div>
        <div className="cols">
          <ul>
            <li><button className="textbtn" onClick={toFinder}>Find platelets</button></li>
            <li><a href="#/finder">Full finder page</a></li>
          </ul>
          <ul>
            <li><a href="#/board">Coordinator board</a></li>
            <li><a href="#/inbox">Message inbox</a></li>
          </ul>
          <ul>
            <li><a href="#/trust">Report trust</a></li>
            <li><a href="#/audit">Audit log</a></li>
          </ul>
          <div className="contact">
            <p>Prototype for VIT Code_Apex 3.0, Team Trex.</p>
            <p>Simulated data · mock channel · not clinically validated. Demo users, not real authentication.</p>
          </div>
        </div>
        <p className="credits">
          Pictures, via Wikimedia Commons: <a href="https://commons.wikimedia.org/w/index.php?curid=93709314">“Platelets collected by using apheresis”</a> by Whoisjohngalt; <a href="https://commons.wikimedia.org/wiki/File:Ambulance_in_India.jpg">“Ambulance in India”</a> by Oleg Yunakov; <a href="https://commons.wikimedia.org/wiki/File:WBC_(neutrophil)_at_centre,_numerous_erythrocytes_and_platelets_(dot_like_bodies)_in_Wright%27s_stained_peripheral_blood_smear_(PBS)_microscopy.jpg">blood smear micrograph</a> by Ajay Kumar Chaurasiya. All <a href="https://creativecommons.org/licenses/by-sa/4.0/">CC BY-SA 4.0</a>, cropped and resized. The board screenshot is this prototype.
        </p>
        <div className="last">
          <span>© 2026 Team Trex. Fictional centres and people.</span>
          <button className="button ink small" onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}>Back to the top</button>
        </div>
      </footer>
    </div>
  );
}
