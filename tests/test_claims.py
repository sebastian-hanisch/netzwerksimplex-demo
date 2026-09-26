"""Jede Zahl, die README, Hilfetexte und Beispieltexte nennen, ist hier belegt (Distributionsnetz 3 Werke, 4 Verteilzentren, 12 Filialen, Seed 1; feste Netze ab Seed 100000).
Die Rechnung ist ganzzahlig und deterministisch: Pivots, Aufwand und Kosten sind auf allen Plattformen dieselben; Mittel über Netze werden mit Bändern geprüft."""

import pytest

import nsx_constants as C
import nsx_evaluation as ev
import nsx_scenario as sc
import nsx_simplex as sx
import nsx_ssp as ssp

P = ev.DEFAULT_PARAMS


def _params(name):
    p = C.PRESETS[name]
    return ev.Params(p["net"], p["plants"], p["dcs"], p["stores"], p["flow"], p["pricing"], p["leaving"], p["big_m"], p["seed"])


def _run(name):
    params = _params(name)
    a = ev.analyse(params)
    return params, a


def test_the_default_network_and_dantzig():
    """25 Knoten, 54 Kanten, 78 Einheiten; Dantzig: 42 Pivots, 24 degeneriert, längste Folge 22, Kosten 1 131 wie Successive Shortest Paths (18 Runden, 1 146 gescannte Kanten), Aufwand 3 761, 57 % künstliche Austritte."""
    params, a = _run("🚚 Distributionsnetz")
    res, net = a["res"], a["net"]
    assert (net.n, net.m, a["value"]) == (25, 54, 78)
    assert (res.n_pivots, res.degenerate, res.longest_stall(), res.cost, res.effort) == (42, 24, 22, 1131, 3761)
    assert (a["ref"].total, a["ref"].n_rounds, a["ref"].scanned_total) == (1131, 18, 1146)
    assert sum(1 for p in res.pivots if p.leaving >= net.m) / res.n_pivots == pytest.approx(0.571, abs=0.001)


def test_diamond_by_hand():
    """Kosten 10, 5 Pivots (3 degeneriert); Successive Shortest Paths 2 Runden (Kosten 3 und 7); S -> A und B -> T sind voll, eine weitere Einheit spart je 2."""
    params, a = _run("💎 Raute")
    res = a["res"]
    assert (res.cost, res.n_pivots, res.degenerate) == (10, 5, 3) and (a["ref"].n_rounds, [r.price for r in a["ref"].rounds]) == (2, [3, 7])
    rows = ev.shadow_rows(a["net"], res, a["value"])
    assert sorted((r["label"], r["value"], r["recomputed"]) for r in rows) == [("B → T", 2, 2), ("S → A", 2, 2)]


def test_assignment_is_degenerate():
    """Kosten 15, 31 Pivots, 23 degeneriert (74 %), längste Folge 9; erste Austrittskante: 34 Pivots, 25 ohne starke Zulässigkeit; 8 Runden bei Successive Shortest Paths."""
    params, a = _run("🧩 Zuordnung")
    res, net = a["res"], a["net"]
    assert (net.n, net.m, res.cost, res.n_pivots, res.degenerate, res.longest_stall()) == (18, 80, 15, 31, 23, 9) and res.degenerate / res.n_pivots == pytest.approx(0.742, abs=0.001)
    lv = ev.compare_leaving(params)
    assert (lv["leaving"]["first"]["pivots"], lv["leaving"]["first"]["violations"]) == (34, 25) and lv["leaving"]["strong"]["violations"] == 0 and a["ref"].n_rounds == 8
    top = ev.shadow_rows(a["net"], res, a["value"])[0]
    assert (top["label"], top["value"], top["recomputed"]) == ("A7 → T", 5, 1)                                # Schattenpreis 5, nach dem Nachrechnen nur 1: die Basis wechselt


def test_the_three_pricing_rules_on_the_default_network():
    """Dantzig 42 Pivots / 3 761, erste verletzte Kante 79 / 1 658, Blocksuche 55 / 1 647 Kantenoperationen; alle Kosten 1 131."""
    c = ev.compare_rules(P)
    assert {r: (v["pivots"], v["effort"]) for r, v in c["rules"].items()} == {"dantzig": (42, 3761), "first": (79, 1658), "block": (55, 1647)}
    assert {v["cost"] for v in c["rules"].values()} == {1131}


def test_first_leaving_arc_loses_strong_feasibility_but_never_cycles():
    """Erste verletzte Kante + erste Austrittskante: 75 Pivots, nach 62 nicht mehr stark zulässig; mit der starken Regel 79 Pivots."""
    params, a = _run("↩️ Erste Austrittskante")
    res = a["res"]
    assert (res.n_pivots, res.strong_violations(), res.hit_limit) == (75, 62, False)
    assert ev.compare_leaving(params)["leaving"]["strong"]["pivots"] == 79


def test_big_m_too_small():
    """M = 4 statt 226: nach 21 degenerierten Pivots 'optimal', 156 Einheiten künstlicher Fluss, echte Kosten 0."""
    params, a = _run("⚠️ Big-M zu klein")
    res = a["res"]
    assert (res.big_m, a["safe_m"], res.n_pivots, res.degenerate, res.artificial_flow, res.cost) == (4, 226, 21, 21, 156, 0) and not res.feasible and res.optimal


def test_the_large_network():
    """56 Knoten, 238 Kanten, 204 Einheiten: Blocksuche 213 Pivots / 8 950, Dantzig 113 / 34 756 (fast das Vierfache), Successive Shortest Paths 12 171 gescannte Kanten in 43 Runden."""
    params, a = _run("🏭 Großes Netz")
    assert (a["net"].n, a["net"].m, a["value"]) == (56, 238, 204)
    c = ev.compare_rules(params)
    assert (c["rules"]["block"]["pivots"], c["rules"]["block"]["effort"], c["rules"]["dantzig"]["pivots"], c["rules"]["dantzig"]["effort"]) == (213, 8950, 113, 34756)
    assert c["rules"]["dantzig"]["effort"] / c["rules"]["block"]["effort"] == pytest.approx(3.88, abs=0.01)
    assert (c["rules"]["first"]["pivots"], c["rules"]["first"]["effort"]) == (281, 8686)                      # die erste verletzte Kante ist auch hier am billigsten
    assert (a["ref"].scanned_total, a["ref"].n_rounds) == (12171, 43)


def test_shadow_prices_of_the_default_network():
    """Die vier größten Schattenpreise 14 / 13 / 12 / 11 (F5 -> T, F9 -> T, F8 -> T, DC 1 -> F12); alle 8 größten stimmen mit dem Nachrechnen (Kapazität + 1) genau überein."""
    a = ev.analyse(P)
    rows = ev.shadow_rows(a["net"], a["res"], a["value"])
    assert [(r["label"], r["value"]) for r in rows[:4]] == [("F5 → T", 14), ("F9 → T", 13), ("F8 → T", 12), ("DC 1 (Ausgang) → F12", 11)]
    assert len(rows) == 8 and all(r["exact"] for r in rows)


def test_size_series_over_five_nets():
    """Pivots Dantzig / erste / Block und Aufwand je Größe; Dantzig 1,6 bis 2,1 Pivots je Knoten; Successive Shortest Paths bei kleinen Netzen billiger als die Blocksuche, ab 44 Knoten teurer."""
    rows = ev.sizes(P)
    assert [r["n"] for r in rows] == [12, 21, 28, 44, 60, 81]
    assert [round(r["pivots"]["dantzig"], 1) for r in rows] == [13.2, 33.8, 50.2, 82.2, 120.4, 172.0]
    assert [round(r["pivots"]["first"], 1) for r in rows] == [16.2, 52.0, 80.0, 188.2, 306.6, 477.0]
    assert [round(r["pivots"]["block"], 1) for r in rows] == [13.8, 44.4, 69.0, 143.4, 240.4, 367.6]
    assert [round(r["effort"]["dantzig"]) for r in rows] == [475, 2419, 5400, 18210, 42501, 98220]
    assert [round(r["effort"]["block"]) for r in rows] == [287, 1130, 2085, 5760, 11796, 21648]
    assert [round(r["effort"]["first"]) for r in rows] == [281, 994, 1666, 5001, 10081, 18565]
    assert [round(r["scanned"]) for r in rows] == [52, 655, 1666, 6325, 16875, 36022] and [round(r["rounds"], 1) for r in rows] == [3.0, 12.8, 20.8, 33.8, 51.0, 67.0]
    ratio = [r["effort"]["block"] / r["scanned"] for r in rows]
    assert ratio[0] == pytest.approx(5.5, abs=0.05) and ratio[1] > 1 and ratio[3] < 1 and ratio[5] == pytest.approx(0.60, abs=0.01)
    per_node = [r["pivots"]["dantzig"] / r["n"] for r in rows[1:]]
    assert per_node == sorted(per_node) and 1.6 <= per_node[0] < 1.65 and 2.1 <= per_node[-1] < 2.15                      # 1,6 bis 2,1 Pivots je Knoten, leicht steigend


def test_distribution_over_40_nets():
    """Pivots Median/Mittel 42/41,9 (Dantzig), 64,5/65,0 (erste), 53/54,0 (Block); Aufwand Median 3 738 / 1 309 / 1 494; kleinster Aufwand in 0 / 35 / 5 Netzen; degenerierter Anteil 60 / 53 / 57 %, längste Folge im Mittel 21,7 / 29,9 / 20,1
    (höchstens 23 / 35 / 27); erste Austrittskante: mehr Pivots in 12 / 32 / 31, weniger in 3 / 8 / 7 Netzen, nie an der Grenze; Big-M bei 2 / 5 / 10 %: 0 / 21 / 40 Netze zulässig; 58 % der Pivots werfen künstliche Kanten hinaus."""
    d = ev.distribution(P)
    assert d["n"] == 40
    assert (d["dantzig"]["pivots_median"], d["first"]["pivots_median"], d["block"]["pivots_median"]) == (42, 64.5, 53)
    assert [round(d[r]["pivots_mean"], 1) for r in ("dantzig", "first", "block")] == [41.9, 65.0, 54.0]
    assert [d[r]["effort_median"] for r in ("dantzig", "first", "block")] == [3738, 1309, 1494]
    assert [d[r]["wins"] for r in ("dantzig", "first", "block")] == [0, 35, 5]
    assert [round(d[r]["deg_mean"], 2) for r in ("dantzig", "first", "block")] == [0.60, 0.53, 0.57]
    assert [round(d[r]["stall_mean"], 1) for r in ("dantzig", "first", "block")] == [21.7, 29.9, 20.1] and [d[r]["stall_max"] for r in ("dantzig", "first", "block")] == [23, 35, 27]
    assert [(d[r]["first_more"], d[r]["first_fewer"]) for r in ("dantzig", "first", "block")] == [(12, 3), (32, 8), (31, 7)] and all(d[r]["first_hit"] == 0 for r in ("dantzig", "first", "block"))
    assert d["m_ok"] == {2: 0, 5: 21, 10: 40} and d["artificial_share"] == pytest.approx(0.576, abs=0.002)


def test_partial_flow_values_cost_less_per_unit():
    """Verlangt man weniger als den größten Fluss, sinken die Kosten je Einheit (die billigsten Wege zuerst): 50 % des Flusses kosten weniger als die Hälfte."""
    net = ev.network(P)
    full = ev.solve(net, ev.flow_value(net, P), P).cost
    half = ev.solve(net, ev.flow_value(net, P._replace(flow=50)), P).cost
    assert half < full / 2


def test_pivots_are_cycle_canceling_steps():
    """Jeder Pivot senkt die Kosten um |c'| theta exakt (Kreisschritt); über die Pivots addiert sich das zum Unterschied zwischen Start- und Endkosten."""
    res = ev.analyse(P)["res"]
    start = res.big_m * sum(res.start_flow[res.n_real:])
    assert start - res.pivots[-1].cost_after == sum(abs(p.reduced) * p.theta for p in res.pivots) and res.pivots[-1].cost_after == res.cost
    assert min(abs(p.reduced) for p in res.pivots) > 0


def test_shadow_prices_over_40_nets():
    """558 volle Kanten in 40 Netzen: bei 525 (94 %) stimmt der Schattenpreis mit dem Nachrechnen (Kapazität + 1) genau überein, sonst liegt die Ersparnis darunter."""
    checked = exact = 0
    for seed in C.SWEEP_SEEDS:
        net = ev.network(P._replace(seed=seed))
        value = ev.flow_value(net, P)
        res = ev.solve(net, value, P)
        for a, (u, v, c, k, kind) in enumerate(net.arcs):
            if res.state[a] == "U" and res.reduced[a] < 0:
                arcs = list(net.arcs)
                arcs[a] = (u, v, c + 1, k, kind)
                more = sx.solve_net(sc.Net(net.names, net.labels, net.pos, tuple(arcs), net.s, net.t, net.logistic), value, trace=False)
                delta = res.cost - more.cost
                assert 0 <= delta <= -res.reduced[a]
                checked += 1
                exact += delta == -res.reduced[a]
    assert (checked, exact) == (558, 525) and exact / checked == pytest.approx(0.94, abs=0.005)


def test_dantzig_effort_is_mostly_pricing_and_the_first_rule_beats_block_everywhere():
    """Bei Dantzig sind im Mittel über 40 Netze 90 % des Aufwands Preissuche; die erste verletzte Kante ist in allen sechs Größen billiger als die Blocksuche; mit der starken Regel spart sie im Mittel 11 % (erste) und 6 % (Block) der Pivots gegenüber der ersten Austrittskante."""
    import statistics
    shares = []
    for seed in C.SWEEP_SEEDS:
        net = ev.network(P._replace(seed=seed))
        r = ev.solve(net, ev.flow_value(net, P), P, pricing="dantzig")
        shares.append(r.examined / r.effort)
    assert statistics.fmean(shares) == pytest.approx(0.90, abs=0.005)
    assert all(r["effort"]["first"] < r["effort"]["block"] for r in ev.sizes(P))
    d = ev.distribution(P)
    assert 1 - d["first"]["pivots_mean"] / d["first"]["first_pivots_mean"] == pytest.approx(0.11, abs=0.005) and 1 - d["block"]["pivots_mean"] / d["block"]["first_pivots_mean"] == pytest.approx(0.06, abs=0.005)
    assert [round(d[r]["first_pivots_mean"], 1) for r in ("dantzig", "first", "block")] == [42.1, 72.8, 57.4] and [round(d[r]["first_violations_mean"]) for r in ("dantzig", "first", "block")] == [9, 59, 43]
