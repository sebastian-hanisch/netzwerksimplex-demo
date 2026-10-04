"""Unabhängiges Orakel: zufällige Kleinstnetze (Parallel- und Gegenkanten, Kapazität 0, Gleichstände) mit beliebiger Bilanz, auch unzulässig, gegen networkx.network_simplex.
Geprüft werden Kosten, Zulässigkeit (Schranken, Flusserhaltung), die Optimalitätsbedingung aus Fluss und Potenzialen (komplementärer Schlupf, unabhängig von `res.state`) und
die Erkennung unzulässiger Netze am künstlichen Fluss. Kosten >= 0: das ist der Bereich der Demo (das sichere Big-M gilt dafür)."""

import random

import pytest

import nsx_simplex as sx

nx = pytest.importorskip("networkx")


def _instance(rng):
    n = rng.randint(2, 8)
    arcs = []
    for _ in range(rng.randint(n - 1, 3 * n)):
        u, v = rng.randrange(n), rng.randrange(n)
        if u != v:
            arcs.append((u, v, rng.choice([0, 1, 1, 2, 3, 4, 5, 7]), rng.choice([rng.randint(0, 9), rng.choice([1, 2])])))
    supply = [0] * n
    for _ in range(rng.randint(0, 3)):
        a, b, q = rng.randrange(n), rng.randrange(n), rng.randint(1, 5)
        supply[a] += q
        supply[b] -= q
    return n, tuple(arcs), supply


def _networkx_cost(n, arcs, supply):
    """Kosten des billigsten Flusses oder None, wenn unzulässig."""
    g = nx.MultiDiGraph()
    for v in range(n):
        g.add_node(v, demand=-supply[v])
    for i, (u, v, c, k) in enumerate(arcs):
        g.add_edge(u, v, key=i, capacity=c, weight=k)
    try:
        return nx.network_simplex(g)[0]
    except nx.NetworkXUnfeasible:
        return None


@pytest.mark.parametrize("pricing,leaving", [("dantzig", "strong"), ("first", "strong"), ("block", "first")])
def test_random_small_nets_against_networkx(pricing, leaving):
    rng = random.Random(20261004)
    feasible = infeasible = 0
    for _ in range(80):
        n, arcs, supply = _instance(rng)
        expected = _networkx_cost(n, arcs, supply)
        res = sx.solve(n, arcs, supply, pricing=pricing, leaving=leaving)
        assert not res.hit_limit
        if expected is None:
            assert not res.feasible and res.artificial_flow > 0
            infeasible += 1
            continue
        feasible += 1
        assert res.feasible and res.artificial_flow == 0 and res.cost == expected
        balance = [0] * n
        for (u, v, c, k), f in zip(arcs, res.flow):
            assert 0 <= f <= c
            balance[u] += f
            balance[v] -= f
            reduced = k + res.potentials[u] - res.potentials[v]
            assert not (reduced > 0 and f != 0) and not (reduced < 0 and f != c)     # komplementärer Schlupf: die Potenziale beweisen die Optimalität
        assert balance == supply
    assert feasible >= 20 and infeasible >= 5
