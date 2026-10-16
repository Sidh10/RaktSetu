"""Test-only replay of raktsetu_sim_v3.run() for parity test P-08 (docs/TESTING.md section 2).

The simulated "world" (random draws, production, posting with ghost units, hospital demand, issuing) is copied from
the simulator. Every DECISION that the prototype ports is delegated to app.core:
  groups.pref_list / tier_map / DIST_*      matching policy and demand shares
  stock.par_levels, surplus_near, own_offerable, listed_view, staleness_bucket
  matcher.greedy_match                      greedy order of needs and candidates
  margin.passes_margin_days                 12-h margin
  trust.after_confirmation / after_visit / estimate
  finder.rank                               family-search ranking
If any of those differ from the simulator, the run record diverges and P-08 fails.
Supports arms A, C, E (not the oracle B or exploratory D) and the greedy matcher, no mis-specified generators.
"""
from __future__ import annotations

import numpy as np

from app.core import finder, groups, margin, matcher, stock, trust

NEVER = -10**9
DEMAND_SHARES = {"WEST": groups.DIST_WEST, "MISMATCH": groups.DIST_NORTH}


class _Centre:
    def __init__(self, dmean, ng, wd):
        self.dmean = dmean
        self.ng = ng
        self.wd = wd
        self.units = []                 # [rem, received_flag, group]
        self.snap = []
        self.snap_day = NEVER
        self.issued_since = []
        self.out_since = [0] * ng

    def posted_day(self):
        return None if self.snap_day < -10**8 else self.snap_day

    def bucket(self, t):
        pd = self.posted_day()
        return stock.staleness_bucket(None if pd is None else t - pd)

    def view(self, day):
        return stock.listed_view(self.snap, self.posted_day(), day, self.out_since, self.ng)

    def own_offerable(self, g):
        return stock.own_offerable(self.units, g, self.dmean * self.wd[g])

    def refresh_snapshot(self, t):
        self.snap = [(r, g) for r, f, g in self.units]
        self.snap_day, self.issued_since = t, []
        self.out_since = [0] * self.ng


def _take_unit(c, prefs):
    for tier, g in enumerate(prefs):
        best = None
        for u in c.units:
            if u[2] == g and (best is None or u[0] < best[0]):
                best = u
        if best is not None:
            c.units.remove(best)
            return best, tier
    return None, None


def run(sim, seed, days, scen, arm, warmup=30, record=None, family=None, groups_set=None, policy="standard",
        rule12=False, q=0.0, Tt=90.0, callog=None, visitlog=None):
    if arm not in ("A", "C", "E"):
        raise NotImplementedError(arm)
    prod, dem, post_u, ghost_u = sim.predraw(seed, days, scen)
    k = len(sim.CENTRES)
    if groups_set is None:
        ng, wd = 1, [1.0]
        pg = [[np.array([int(prod[i, t])]) for t in range(days)] for i in range(k)]
        dg = [[[0] * int(dem[i, t]) for t in range(days)] for i in range(k)]
        prefs = {0: [0]}
    else:
        ng, wd = 8, DEMAND_SHARES[groups_set]
        pg, dg = sim.predraw_groups(seed, days, prod, dem, groups_set)
        prefs = {g: groups.pref_list(g, policy) for g in range(8)}
    tier_of = groups.tier_map(policy, ng)
    e_eff, u_eff, phantom = sim.predraw_misspec(seed, days, scen, None, None)
    post = post_u < u_eff
    rr3 = np.random.default_rng([seed, 47])
    resp_u = rr3.random((days, 512, 2))
    resp_d = rr3.exponential(15.0, (days, 512, 2))

    cs = [_Centre(c[1], ng, wd) for c in sim.CENTRES]
    par = [stock.par_levels(c.dmean, wd) for c in cs]
    a = np.full((k, 3), 2.0)
    b = np.full((k, 3), 1.0)
    m = dict(produced=0, demanded=0, unmet=0, expired=0, trips=0, wasted=0,
             calls=0, moved=0, families=0, fam_served=0, fam_failed_visits=0,
             calls_bundled=0, attempts=0, call_short=0, call_zero=0, call_dropped=0,
             blocked_12h=0, tconf_sum=0.0, tconf_n=0, issues=0, abo_nonid=0, antiD=0,
             req_by_group=[0] * ng, unmet_by_group=[0] * ng)
    fa = [[trust.PRIOR_ALPHA] * trust.N_BUCKETS for _ in range(k)]
    fb = [[trust.PRIOR_BETA] * trust.N_BUCKETS for _ in range(k)]

    def issue(u, g, live):
        if live:
            m["issues"] += 1
            if not groups.is_abo_identical(g, u[2]):
                m["abo_nonid"] += 1
            if groups.is_anti_d(g, u[2]):
                m["antiD"] += 1

    for t in range(days):
        live = t >= warmup
        for c in cs:
            nu = []
            for r, f, g in c.units:
                r -= 1
                if r <= 0:
                    if live:
                        m["expired"] += 1
                else:
                    nu.append([r, f, g])
            c.units = nu
        for i, c in enumerate(cs):
            for g in range(ng):
                c.units += [[stock.SHELF, False, g] for _ in range(int(pg[i][t][g]))]
            if live:
                m["produced"] += int(prod[i, t])
        for i, c in enumerate(cs):
            if post[i, t]:
                listed = [(r, g) for r, f, g in c.units]
                for j, (r_iss, d_iss, g) in enumerate(c.issued_since):
                    if j < 64 and ghost_u[i, t, j] < e_eff[i, t]:
                        rr = r_iss - (t - d_iss)
                        if rr > 0:
                            listed.append((rr, g))
                listed += phantom[i][t]
                c.snap, c.snap_day = listed, t
                c.issued_since, c.out_since = [], [0] * ng
        if arm != "A":
            bundled = set()
            needs = []
            for j, c in enumerate(cs):
                stk = [0] * ng
                for u in c.units:
                    stk[u[2]] += 1
                for g, need in enumerate(stock.needs_from_par(par[j], stk)):
                    if need > 0:
                        needs.append([need, j, g])
            true_rel = {(i, h): cs[i].own_offerable(h) for i in range(k) for h in range(ng)}
            offers = {}
            for i, c in enumerate(cs):
                vw = c.view(t)
                for h in range(ng):
                    off = stock.surplus_near(vw[h], c.dmean * wd[h])
                    if off:
                        offers[(i, h)] = len(off)
            ctr = [0]

            def attempt(key, j, need):
                i, h = key
                req = min(need, offers[key])
                c = cs[i]
                stale = c.bucket(t)
                confirm = arm == "E"
                true_off = true_rel[key]
                tconf = 0.0
                if confirm:
                    if live:
                        m["calls"] += 1
                        if (i, j) not in bundled:
                            bundled.add((i, j))
                            m["calls_bundled"] += 1
                    idx = min(ctr[0], 511)
                    ctr[0] += 1
                    answered = False
                    for att in range(2):
                        if live:
                            m["attempts"] += 1
                        if resp_u[t, idx, att] >= q:
                            tconf = 60.0 * att + resp_d[t, idx, att]
                            answered = True
                            break
                    if not answered:
                        if live:
                            m["call_dropped"] += 1
                        return 0
                    if live:
                        m["tconf_sum"] += tconf
                        m["tconf_n"] += 1
                    found_call = min(req, len(true_off))
                    if live:
                        m["call_short"] += found_call < req
                        m["call_zero"] += found_call == 0
                    if callog is not None and live:
                        callog.append((t, i, j, h, req, found_call, tconf))
                    fa[i][stale], fb[i][stale] = trust.after_confirmation(fa[i][stale], fb[i][stale], req, found_call)
                    c.refresh_snapshot(t)
                    for hh in range(ng):
                        kk = (i, hh)
                        if kk in offers or true_rel[kk]:
                            offers[kk] = len(true_rel[kk])
                    if found_call == 0:
                        return 0
                    req = found_call
                if rule12:
                    n_ok = sum(1 for r in true_off if margin.passes_margin_days(r, tconf, Tt))
                else:
                    n_ok = len(true_off)
                found = min(req, n_ok)
                if rule12 and live:
                    m["blocked_12h"] += min(req, len(true_off)) - found
                if confirm and found == 0:
                    offers[key] = max(0, offers[key] - req)
                    return 0
                if live:
                    m["trips"] += 1
                    if found == 0:
                        m["wasted"] += 1
                if found > 0:
                    true_off.sort(reverse=True)
                    moved, true_rel[key] = true_off[:found], true_off[found:]
                    for r in moved:
                        for u in c.units:
                            if u[0] == r and not u[1] and u[2] == h:
                                c.units.remove(u)
                                break
                        cs[j].units.append([r, True, h])
                    c.out_since[h] += found
                    if live:
                        m["moved"] += found
                offers[key] = max(0, offers[key] - req)
                return found

            matcher.greedy_match(needs, offers, tier_of, attempt)
        unmet_today = [[] for _ in range(k)]
        for i, c in enumerate(cs):
            reqs = dg[i][t]
            if live:
                m["demanded"] += len(reqs)
            if ng == 1:
                c.units.sort(key=lambda u: u[0])
                use = min(len(reqs), len(c.units))
                for u in c.units[:use]:
                    c.issued_since.append((u[0], t, u[2]))
                    issue(u, 0, live)
                c.units = c.units[use:]
                unmet_today[i] = [0] * (len(reqs) - use)
            else:
                for g in reqs:
                    if live:
                        m["req_by_group"][g] += 1
                    u, tier = _take_unit(c, prefs[g])
                    if u is None:
                        unmet_today[i].append(g)
                    else:
                        c.issued_since.append((u[0], t, u[2]))
                        issue(u, g, live)
        if family is not None:
            for o in range(k):
                still = []
                for g in unmet_today[o]:
                    if live:
                        m["families"] += 1
                    cands = []
                    for i, c in enumerate(cs):
                        if i == o:
                            continue
                        vw = c.view(t)
                        listed = sum(len(vw[h]) for h in prefs[g])
                        st = c.bucket(t)
                        cands.append(finder.FinderCandidate(i, listed, trust.estimate(fa[i][st], fb[i][st]), st))
                    served = False
                    for cd in finder.rank(cands, "raw" if family == "naive" else "trust")[:finder.VISIT_TOP_N]:
                        i, st, listed, rel = cd.centre, cd.bucket, cd.listed, cd.p
                        c = cs[i]
                        ok = bool(c.units) if ng == 1 else any(u[2] in tier_of[g] for u in c.units)
                        if visitlog is not None and live:
                            visitlog.append((rel, int(ok), listed, i, st))
                        if ok:
                            if ng == 1:
                                c.units.sort(key=lambda u: u[0])
                                u = c.units.pop(0)
                            else:
                                u, _t = _take_unit(c, prefs[g])
                            c.issued_since.append((u[0], t, u[2]))
                            issue(u, g, live)
                            fa[i][st], fb[i][st] = trust.after_visit(fa[i][st], fb[i][st], True)
                            served = True
                            if live:
                                m["fam_served"] += 1
                            break
                        fa[i][st], fb[i][st] = trust.after_visit(fa[i][st], fb[i][st], False)
                        if live:
                            m["fam_failed_visits"] += 1
                    if not served:
                        still.append(g)
                unmet_today[o] = still
        if live:
            m["unmet"] += sum(len(x) for x in unmet_today)
            if ng > 1:
                for x in unmet_today:
                    for g in x:
                        m["unmet_by_group"][g] += 1
        if record is not None:
            faa, fbb = np.array(fa), np.array(fb)
            record.append(dict(day=t, stocks=[sorted(r for r, f, g in c.units) for c in cs],
                               snap_age=[t - c.snap_day for c in cs],
                               trust=(a / (a + b)).round(3).tolist(),
                               ftrust=(faa / (faa + fbb)).round(3).tolist(),
                               m=dict(m)))
    return m
