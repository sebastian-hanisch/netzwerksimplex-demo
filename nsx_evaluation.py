"""Auswertung: Netzwerksimplex mit den gewählten Regeln, Preisregeln im Vergleich, Austrittsregeln, Schattenpreise mit Gegenprobe, Aufwand gegen Netzgröße, Verteilungen über feste Netze.
Alle Zufallsnetze kommen aus festen Seeds (nsx_constants), unabhängig vom Nutzer-Seed."""

import statistics
from collections import namedtuple

import nsx_constants as C
import nsx_edmonds_karp as ek
import nsx_scenario as sc
import nsx_simplex as sx
import nsx_ssp as ssp

Params = namedtuple("Params", "net plants dcs stores flow pricing leaving big_m seed")
DEFAULT_PARAMS = Params(C.DEFAULT_NET, C.DEFAULT_PLANTS, C.DEFAULT_DCS, C.DEFAULT_STORES, C.DEFAULT_FLOW, C.DEFAULT_PRICING, C.DEFAULT_LEAVING, C.DEFAULT_BIG_M, C.DEFAULT_SEED)


def network(params):
    if params.net == "diamond":
        return sc.diamond_cost()
    if params.net == "assignment":
        return sc.assignment_cost(C.ASSIGNMENT_N)
    return sc.generate(params.plants, params.dcs, params.stores, C.DENSITY, C.SPREAD, C.LOAD, params.seed)


def max_value(net):
    return ek.max_flow(net, keep_flows=False).value


def flow_value(net, params):
    """Flusswert: beim Distributionsnetz der gewählte Anteil des maximalen Flusses, bei den Lehrnetzen der maximale Fluss."""
    top = max_value(net)
    return max(1, top * params.flow // 100) if net.logistic else top


def arcs_of(net):
    return tuple((u, v, c, k) for u, v, c, k, _kind in net.arcs)


def big_m_of(net, pct):
    return max(1, sx.default_big_m(arcs_of(net), net.n) * pct // 100)


def solve(net, value, params, pricing=None, leaving=None, trace=False, pct=None):
    return sx.solve_net(net, value, pricing=pricing or params.pricing, leaving=leaving or params.leaving, big_m=big_m_of(net, params.big_m if pct is None else pct), trace=trace)


def analyse(params):
    """Netzwerksimplex mit Trace, dazu Successive Shortest Paths auf demselben Netz (Runden, gescannte Kanten, Kosten) als Gegenprobe."""
    net = network(params)
    value = flow_value(net, params)
    res = solve(net, value, params, trace=True)
    ref = ssp.ssp(net, target=value, keep_trace=False)
    return dict(net=net, value=value, top=max_value(net), res=res, ref=ref, big_m=res.big_m, safe_m=sx.default_big_m(arcs_of(net), net.n), match=res.feasible and res.cost == ref.total)


def compare_rules(params):
    """Alle drei Preisregeln auf demselben Netz mit der gewählten Austrittsregel: Pivots, Aufwand nach Art, degenerierte Pivots, längste Stillstandsfolge."""
    net = network(params)
    value = flow_value(net, params)
    out = {}
    for rule in sx.PRICING:
        r = solve(net, value, params, pricing=rule)
        out[rule] = dict(pivots=r.n_pivots, effort=r.effort, examined=r.examined, cycle=r.cycle_steps, updated=r.updated, degenerate=r.degenerate, stall=r.longest_stall(), cost=r.cost, feasible=r.feasible)
    return dict(net=net, value=value, rules=out)


def compare_leaving(params):
    """Beide Austrittsregeln mit der gewählten Preisregel: Pivots, Aufwand, degenerierte Pivots, Stillstand, Zahl der Pivots mit verletzter starker Zulässigkeit."""
    net = network(params)
    value = flow_value(net, params)
    out = {}
    for rule in sx.LEAVING:
        r = solve(net, value, params, leaving=rule, trace=True)
        out[rule] = dict(pivots=r.n_pivots, effort=r.effort, degenerate=r.degenerate, stall=r.longest_stall(), violations=r.strong_violations(), hit_limit=r.hit_limit, cost=r.cost)
    return dict(net=net, value=value, leaving=out)


def arc_label(net, a):
    u, v, *_r = net.arcs[a]
    return f"{net.labels[u] or net.names[u]} → {net.labels[v] or net.names[v]}"


def shadow_rows(net, res, value, top=8, check=True):
    """Volle Kanten mit reduzierten Kosten c' < 0: Wert einer weiteren Einheit Kapazität = -c'. Gegenprobe (`check`) für die `top` größten: Kapazität + 1 und neu rechnen."""
    rows = []
    for a, (u, v, c, k, kind) in enumerate(net.arcs):
        if res.state[a] == "U" and res.reduced[a] < 0:
            rows.append(dict(arc=a, label=arc_label(net, a), capacity=c, value=-res.reduced[a], kind=kind))
    rows.sort(key=lambda r: (-r["value"], r["arc"]))
    rows = rows[:top]
    if check:
        for r in rows:
            arcs = list(net.arcs)
            u, v, c, k, kind = arcs[r["arc"]]
            arcs[r["arc"]] = (u, v, c + 1, k, kind)
            more = sx.solve_net(sc.Net(net.names, net.labels, net.pos, tuple(arcs), net.s, net.t, net.logistic), value, trace=False)
            r["recomputed"] = res.cost - more.cost
            r["exact"] = r["recomputed"] == r["value"]
    return rows


def sizes(params, sizes=C.SIZES, seeds=C.SIZE_SEEDS):
    """Pivots und Aufwand je Preisregel gegen die Netzgröße (Mittel über feste Netze) und Successive Shortest Paths (Runden, gescannte Kanten)."""
    rows = []
    for (p_, d_, s_) in sizes:
        per = []
        for seed in seeds:
            net = sc.generate(p_, d_, s_, C.DENSITY, C.SPREAD, C.LOAD, seed)
            value = max_value(net)
            rs = {rule: sx.solve_net(net, value, pricing=rule, leaving=params.leaving, trace=False) for rule in sx.PRICING}
            ref = ssp.ssp(net, target=value, keep_trace=False)
            per.append(dict(n=net.n, m=net.m, pivots={r_: r.n_pivots for r_, r in rs.items()}, effort={r_: r.effort for r_, r in rs.items()}, rounds=ref.n_rounds, scanned=ref.scanned_total))
        rows.append(dict(size=(p_, d_, s_), n=per[0]["n"], m=statistics.fmean(x["m"] for x in per),
                         pivots={r: statistics.fmean(x["pivots"][r] for x in per) for r in sx.PRICING}, effort={r: statistics.fmean(x["effort"][r] for x in per) for r in sx.PRICING},
                         rounds=statistics.fmean(x["rounds"] for x in per), scanned=statistics.fmean(x["scanned"] for x in per)))
    return rows


def distribution(params, seeds=C.SWEEP_SEEDS):
    """Über feste Netze mit den gewählten Größen: je Preisregel Pivots, Aufwand, degenerierter Anteil, Stillstand; wie oft eine Regel den kleinsten Aufwand hat; Austrittsregeln gegeneinander; Big-M-Schwelle."""
    rows = []
    for seed in seeds:
        net = network(params._replace(net="distribution", seed=seed))
        value = flow_value(net, params)
        row = {}
        for rule in sx.PRICING:
            r = solve(net, value, params, pricing=rule, leaving="strong")
            f = solve(net, value, params, pricing=rule, leaving="first", trace=True)
            row[rule] = dict(pivots=r.n_pivots, effort=r.effort, deg=r.degenerate / r.n_pivots if r.n_pivots else 0.0, stall=r.longest_stall(), first_pivots=f.n_pivots, first_violations=f.strong_violations(), first_hit=f.hit_limit)
        row["m_ok"] = {pct: solve(net, value, params, pct=pct, pricing="dantzig").feasible for pct in (2, 5, 10)}
        row["artificial_share"] = statistics.fmean([1.0 if p.leaving >= net.m else 0.0 for p in solve(net, value, params, pricing="dantzig", trace=True).pivots])
        rows.append(row)
    out = dict(n=len(rows), rows=rows)
    for rule in sx.PRICING:
        out[rule] = dict(
            pivots_mean=statistics.fmean(r[rule]["pivots"] for r in rows), pivots_median=statistics.median(r[rule]["pivots"] for r in rows),
            effort_mean=statistics.fmean(r[rule]["effort"] for r in rows), effort_median=statistics.median(r[rule]["effort"] for r in rows),
            deg_mean=statistics.fmean(r[rule]["deg"] for r in rows), stall_mean=statistics.fmean(r[rule]["stall"] for r in rows), stall_max=max(r[rule]["stall"] for r in rows),
            wins=sum(1 for r in rows if r[rule]["effort"] == min(r[x]["effort"] for x in sx.PRICING)),
            first_more=sum(1 for r in rows if r[rule]["first_pivots"] > r[rule]["pivots"]), first_fewer=sum(1 for r in rows if r[rule]["first_pivots"] < r[rule]["pivots"]),
            first_pivots_mean=statistics.fmean(r[rule]["first_pivots"] for r in rows), first_violations_mean=statistics.fmean(r[rule]["first_violations"] for r in rows), first_hit=sum(1 for r in rows if r[rule]["first_hit"]))
    out["m_ok"] = {pct: sum(1 for r in rows if r["m_ok"][pct]) for pct in (2, 5, 10)}
    out["artificial_share"] = statistics.fmean(r["artificial_share"] for r in rows)
    return out


def step_view(res, k):
    """Zustand VOR Pivot k (1-basiert) für die Karte: (Pivot, Status je Kante, Potenziale)."""
    p = res.pivots[k - 1]
    if k == 1:
        return p, res.start_state, res.start_potentials
    prev = res.pivots[k - 2]
    return p, prev.state, prev.potentials
