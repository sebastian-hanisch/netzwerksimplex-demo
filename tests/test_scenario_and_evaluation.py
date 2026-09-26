"""Szenario (Netze, Lehrnetze, Zufallsstrom) und Auswertung (Analyse, Preisregeln, Austrittsregeln, Schattenpreise, Größen, Verteilung)."""

import pytest

import nsx_constants as C
import nsx_evaluation as ev
import nsx_scenario as sc

P = ev.DEFAULT_PARAMS


def test_generation_is_deterministic_and_seed_dependent():
    a, b, c = sc.generate(3, 4, 12, 60, 50, 100, 5), sc.generate(3, 4, 12, 60, 50, 100, 5), sc.generate(3, 4, 12, 60, 50, 100, 6)
    assert a == b and a != c


def test_network_dispatch_and_flow_value():
    assert ev.network(P) == sc.generate(3, 4, 12, C.DENSITY, C.SPREAD, C.LOAD, 1) and ev.network(P).n == 25
    assert ev.network(P._replace(net="diamond")).n == 4 and ev.network(P._replace(net="assignment")).n == 18
    net = ev.network(P)
    assert ev.flow_value(net, P) == ev.max_value(net) == 78 and ev.flow_value(net, P._replace(flow=50)) == 39
    assert ev.flow_value(sc.diamond_cost(), P._replace(flow=10)) == 2                      # Lehrnetze: immer der maximale Fluss


def test_analyse_matches_successive_shortest_paths():
    a = ev.analyse(P)
    assert a["match"] and a["res"].feasible and a["res"].cost == a["ref"].total and a["big_m"] == a["safe_m"]
    bad = ev.analyse(P._replace(big_m=2))
    assert not bad["match"] and not bad["res"].feasible and bad["big_m"] < bad["safe_m"]


def test_compare_rules_and_leaving_shapes():
    c = ev.compare_rules(P)
    assert set(c["rules"]) == {"dantzig", "first", "block"} and len({v["cost"] for v in c["rules"].values()}) == 1
    assert all(v["effort"] == v["examined"] + v["cycle"] + v["updated"] for v in c["rules"].values())
    lv = ev.compare_leaving(P)
    assert set(lv["leaving"]) == {"strong", "first"} and lv["leaving"]["strong"]["violations"] == 0 and lv["leaving"]["strong"]["cost"] == lv["leaving"]["first"]["cost"]


def test_shadow_rows_are_sorted_and_checked_by_recomputation():
    a = ev.analyse(P)
    rows = ev.shadow_rows(a["net"], a["res"], a["value"])
    assert 1 <= len(rows) <= 8 and [r["value"] for r in rows] == sorted((r["value"] for r in rows), reverse=True)
    assert all(0 <= r["recomputed"] <= r["value"] for r in rows)
    assert ev.shadow_rows(a["net"], a["res"], a["value"], check=False)[0].get("recomputed") is None


def test_step_view_before_the_pivot():
    a = ev.analyse(P)
    res = a["res"]
    p, state, pot = ev.step_view(res, 1)
    assert state == res.start_state and pot == res.start_potentials and p is res.pivots[0]
    p2, state2, pot2 = ev.step_view(res, 5)
    assert state2 == res.pivots[3].state and pot2 == res.pivots[3].potentials and p2 is res.pivots[4]
    assert state2[p2.entering] in ("L", "U") and state2[p2.leaving] == "T" or p2.entering == p2.leaving


def test_sizes_and_distribution_shapes():
    rows = ev.sizes(P, sizes=((2, 2, 4), (3, 4, 8)), seeds=C.SIZE_SEEDS[:2])
    assert [r["n"] for r in rows] == [12, 21] and rows[0]["pivots"]["dantzig"] < rows[1]["pivots"]["dantzig"] and rows[0]["scanned"] < rows[1]["scanned"]
    d = ev.distribution(P, seeds=C.SWEEP_SEEDS[:4])
    assert d["n"] == 4 and set(d["m_ok"]) == {2, 5, 10} and sum(d[r]["wins"] for r in ("dantzig", "first", "block")) >= 4
    assert 0 <= d["artificial_share"] <= 1 and d["m_ok"][10] == 4


def test_arc_label():
    net = sc.diamond_cost()
    assert ev.arc_label(net, 0) == "S → A" and ev.arc_label(net, 4) == "B → T"
