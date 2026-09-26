"""Netzwerksimplex: Raute von Hand, Gleichheit mit Successive Shortest Paths und networkx, Baum-Invarianten nach jedem Pivot, Kostensenkung, starke Zulässigkeit, Big-M-Kontrolle, Zähler."""

import networkx as nx
import pytest

import nsx_edmonds_karp as ek
import nsx_scenario as sc
import nsx_simplex as sx
import nsx_ssp as ssp

NETS = [sc.generate(3, 4, 12, 60, 50, 100, s) for s in range(1, 7)] + [sc.generate(2, 2, 5, 80, 50, 100, 9), sc.generate(4, 5, 16, 60, 50, 100, 2)]


def _arcs(net):
    return tuple((u, v, c, k) for u, v, c, k, _kind in net.arcs)


def _supply(net, value):
    b = [0] * net.n
    b[net.s], b[net.t] = value, -value
    return b


def _flow_value(net):
    return ek.max_flow(net, keep_flows=False).value


def test_diamond_by_hand():
    """Zwei Einheiten S -> T: S-A-T und S-B-T kosten 5 + 5 = 10; die billigste Einzelrunde S-A-B-T (3) wird durch die zweite Einheit teilweise zurückgenommen."""
    net = sc.diamond_cost()
    r = sx.solve_net(net, 2)
    assert (r.cost, r.flow, r.feasible, r.artificial_flow) == (10, (1, 1, 0, 1, 1), True, 0)
    assert sx.certificate(net.n, _arcs(net), _supply(net, 2), r)[0]
    one = sx.solve_net(net, 1)
    assert one.cost == 3 and one.flow == (1, 0, 1, 0, 1)


@pytest.mark.parametrize("pricing", sx.PRICING)
@pytest.mark.parametrize("leaving", sx.LEAVING)
def test_costs_equal_successive_shortest_paths(pricing, leaving):
    for net in NETS:
        F = _flow_value(net)
        r = sx.solve_net(net, F, pricing=pricing, leaving=leaving)
        assert r.feasible and r.optimal and not r.hit_limit
        assert r.cost == ssp.ssp(net, target=F, keep_trace=False).total
        assert sx.certificate(net.n, _arcs(net), _supply(net, F), r)[0]


def test_cost_equals_networkx():
    net = NETS[0]
    F = _flow_value(net)
    G = nx.DiGraph()
    for v in range(net.n):
        G.add_node(v, demand=-F if v == net.s else F if v == net.t else 0)
    for u, v, c, k, _kind in net.arcs:
        G.add_edge(u, v, capacity=c, weight=k)
    assert nx.min_cost_flow_cost(G) == sx.solve_net(net, F).cost


def test_all_pricing_rules_reach_the_same_cost_for_partial_flow_values():
    net = NETS[1]
    F = _flow_value(net)
    for value in (1, F // 3, F // 2, F):
        costs = {sx.solve_net(net, value, pricing=p).cost for p in sx.PRICING}
        assert len(costs) == 1 and costs == {ssp.ssp(net, target=value, keep_trace=False).total}


def _replay(net, value, res):
    """Baut aus dem Trace nach jedem Pivot den Baum neu auf und prüft alle Invarianten unabhängig vom Verfahren."""
    n, m = net.n, net.m
    root = n
    supply = _supply(net, value)
    tail = [a[0] for a in net.arcs] + [v if supply[v] >= 0 else root for v in range(n)]
    head = [a[1] for a in net.arcs] + [root if supply[v] >= 0 else v for v in range(n)]
    cap = [a[2] for a in net.arcs] + [sum(abs(b) for b in supply) + 1] * n
    cost = [a[3] for a in net.arcs] + [res.big_m] * n
    prev_cost = sum(f * c for f, c in zip(res.start_flow, cost))
    for p in res.pivots:
        tree = [a for a in range(m + n) if p.state[a] == "T"]
        assert len(tree) == n                                                        # n + 1 Knoten: n Baumkanten
        adj = {v: [] for v in range(n + 1)}
        for a in tree:
            adj[tail[a]].append((head[a], a, 1))
            adj[head[a]].append((tail[a], a, -1))
        pot, seen, stack = {root: 0}, {root}, [root]
        while stack:
            z = stack.pop()
            for y, a, sign in adj[z]:
                if y not in seen:
                    seen.add(y)
                    pot[y] = pot[z] + sign * cost[a]
                    stack.append(y)
        assert len(seen) == n + 1                                                    # spannt alle Knoten, ist zusammenhängend
        assert tuple(pot[v] for v in range(n)) == p.potentials
        bal = [0] * (n + 1)
        for a in range(m + n):
            assert 0 <= p.flow[a] <= cap[a]
            bal[tail[a]] += p.flow[a]
            bal[head[a]] -= p.flow[a]
            if p.state[a] == "L":
                assert p.flow[a] == 0
            if p.state[a] == "U":
                assert p.flow[a] == cap[a]
        assert bal[:n] == supply                                                     # Flusserhaltung inklusive künstlicher Kanten
        cur = sum(f * c for f, c in zip(p.flow, cost))
        assert cur == p.cost_after == prev_cost - abs(p.reduced) * p.theta           # Kostensenkung um |c'| theta
        prev_cost = cur
    return True


@pytest.mark.parametrize("pricing", sx.PRICING)
def test_tree_potentials_flows_and_cost_drop_after_every_pivot(pricing):
    for net in NETS[:4] + [sc.diamond_cost(), sc.assignment_cost(5)]:
        F = _flow_value(net)
        assert _replay(net, F, sx.solve_net(net, F, pricing=pricing))
        assert _replay(net, F, sx.solve_net(net, F, pricing=pricing, leaving="first"))


def test_the_strong_rule_keeps_the_basis_strongly_feasible_and_the_first_rule_does_not():
    bad = 0
    for net in NETS + [sc.assignment_cost(5), sc.assignment_cost(8)]:
        F = _flow_value(net)
        for pricing in sx.PRICING:
            assert sx.solve_net(net, F, pricing=pricing, leaving="strong").strong_violations() == 0
            bad += sx.solve_net(net, F, pricing=pricing, leaving="first").strong_violations()
    assert bad > 0


def test_big_m_too_small_leaves_artificial_flow_and_is_detected():
    net = NETS[0]
    F = _flow_value(net)
    base = sx.default_big_m(_arcs(net), net.n)
    ok = sx.solve_net(net, F)
    assert ok.feasible and ok.artificial_flow == 0 and ok.big_m == base
    for pct in (1, 2):
        bad = sx.solve_net(net, F, big_m=max(1, base * pct // 100))
        assert bad.optimal and not bad.feasible and bad.artificial_flow > 0
    assert sx.solve_net(net, F, big_m=base * 10 // 100).feasible


def test_infeasible_demand_is_reported_instead_of_a_wrong_flow():
    net = NETS[0]
    r = sx.solve_net(net, _flow_value(net) + 5)
    assert not r.feasible and r.artificial_flow > 0


def test_counters_and_limits():
    net = NETS[2]
    F = _flow_value(net)
    r = sx.solve_net(net, F, pricing="block")
    assert r.examined == sum(p.examined for p in r.pivots) + r.final_examined
    assert r.effort == r.examined + r.cycle_steps + r.updated and r.cycle_steps == sum(p.cycle_steps for p in r.pivots) and r.updated == sum(p.updated for p in r.pivots)
    limited = sx.solve_net(net, F, max_pivots=3)
    assert limited.hit_limit and limited.n_pivots == 3 and not limited.optimal
    assert sx.solve_net(net, F, trace=False).cost == sx.solve_net(net, F).cost


def test_dantzig_prices_every_arc_every_time_and_block_far_fewer():
    net = NETS[1]
    F = _flow_value(net)
    d = sx.solve_net(net, F, pricing="dantzig")
    assert all(p.examined == net.m + net.n for p in d.pivots) and d.final_examined == net.m + net.n
    b = sx.solve_net(net, F, pricing="block")
    assert sum(p.examined for p in b.pivots) / b.n_pivots < 0.5 * (net.m + net.n)


def test_deterministic_and_integral():
    net = NETS[3]
    F = _flow_value(net)
    a, b = sx.solve_net(net, F, pricing="block"), sx.solve_net(net, F, pricing="block")
    assert a.pivots == b.pivots and a.cost == b.cost
    assert all(isinstance(x, int) for x in a.flow) and all(isinstance(x, int) for x in a.potentials)


def test_shadow_prices_by_recomputation():
    """Volle Kante mit reduzierten Kosten c' < 0: eine Einheit mehr Kapazität senkt die Kosten um höchstens |c'| (Subgradient), in den meisten Fällen genau |c'|."""
    net = NETS[1]
    F = _flow_value(net)
    r = sx.solve_net(net, F)
    checked = exact = 0
    for a, (u, v, c, k, kind) in enumerate(net.arcs):
        if r.state[a] == "U" and r.reduced[a] < 0:
            arcs = list(net.arcs)
            arcs[a] = (u, v, c + 1, k, kind)
            more = sx.solve_net(sc.Net(net.names, net.labels, net.pos, tuple(arcs), net.s, net.t, net.logistic), F)
            delta = more.cost - r.cost
            assert r.reduced[a] <= delta <= 0
            checked += 1
            exact += delta == r.reduced[a]
    assert checked >= 3 and exact >= checked // 2


def test_assignment_is_highly_degenerate_and_all_flows_are_binary():
    net = sc.assignment_cost(5)
    r = sx.solve_net(net, 5)
    assert r.cost == ssp.ssp(net, target=5, keep_trace=False).total and set(r.flow) <= {0, 1}
    assert r.degenerate >= r.n_pivots // 2
