"""Die aus den Vorgängern kopierten Bausteine (Zufallsgenerator, Netz, Successive Shortest Paths, Max-Flow) sind bewacht: dieselben Zahlen wie in ssp-demo."""

import nsx_edmonds_karp as ek
import nsx_scenario as sc
import nsx_ssp as ssp


def test_splitmix64_stream_is_the_portfolio_standard():
    rng = sc.SplitMix64(1)
    assert [rng.next() for _ in range(2)] == [10451216379200822465, 13757245211066428519]


def test_ssp_reproduces_the_diamond_of_ssp_demo():
    """ssp-demo, Raute mit Kosten: die erste Einheit fährt über S-A-B-T (3), die zweite nimmt A->B zurück: 4 - 1 + 4 = 7, insgesamt 10."""
    res = ssp.ssp(sc.diamond_cost())
    assert (res.value, res.total, [r.price for r in res.rounds], [r.uses_back_arc for r in res.rounds]) == (2, 10, [3, 7], [False, True])


def test_max_flow_of_the_diamond_and_the_assignment():
    assert ek.max_flow(sc.diamond_cost(), keep_flows=False).value == 2
    assert ek.max_flow(sc.assignment_cost(5), keep_flows=False).value == 5
