"""Netzwerksimplex: kostenminimaler Fluss durch Pivots auf einer Spannbaum-Basis.

**Basis = Spannbaum.** Jede Basislösung eines Min-Cost-Flow-Problems ist ein Spannbaum der Knoten; alle Kanten außerhalb des Baums liegen an ihrer unteren (L, Fluss 0) oder oberen (U, Fluss = Kapazität) Schranke,
der Fluss auf den Baumkanten folgt eindeutig aus der Flusserhaltung. Zum Baum gehören **Potenziale** pi (pi(Wurzel) = 0, entlang jeder Baumkante (u, v) gilt pi(v) = pi(u) + Kosten) und je Kante die **reduzierten Kosten**
c' = Kosten + pi(u) - pi(v): die Kosten des Kreises, den die Kante mit dem Baum bildet, je Einheit Fluss.
**Optimal**, wenn keine Nicht-Baum-Kante an L ein c' < 0 und keine an U ein c' > 0 hat. Die Potenziale sind die **Schattenpreise**: eine volle Kante (c' < 0) spart je zusätzlicher Einheit Kapazität |c'|.

**Ein Pivot** nimmt eine verletzte Kante e (die **eintretende**), schließt sie mit dem Baumpfad zum **Kreis**, verschiebt Fluss um das Maximum theta, das eine Kante des Kreises an ihre Schranke bringt (die **austretende** Kante),
und tauscht e gegen sie im Baum. Die Kosten fallen um |c'| theta; ist theta = 0, ist der Pivot **degeneriert** (der Baum ändert sich, der Fluss nicht). Jeder Pivot ist ein Cycle-Canceling-Schritt, dessen Kreis von den reduzierten Kosten gewählt wird.
Nur der abgetrennte Teilbaum bekommt neue Tiefen und Potenziale.

**Start:** eine künstliche Wurzel R mit einer künstlichen Kante je Knoten (Kosten M, Kapazität unbeschränkt): Knoten mit Überschuss schicken ihn zur Wurzel, Knoten mit Bedarf holen ihn von dort, Knoten mit Bilanz 0 hängen mit Fluss 0 an R (Kante zur Wurzel hin).
Das ist immer ein zulässiger Baum; ist M groß genug, drücken die Pivots den künstlichen Fluss auf 0 (**Big-M**). Bleibt er positiv, hat das Netz keine zulässige Lösung - oder M war zu klein (Negativkontrolle).

**Preisregeln** (welche verletzte Kante eintritt): `dantzig` prüft alle Kanten und nimmt die größte Verletzung; `first` sucht zyklisch ab der letzten Stelle und nimmt die erste verletzte; `block` prüft Blöcke von etwa Wurzel(m) Kanten
und nimmt die beste des ersten Blocks mit einer verletzten Kante. **Austrittsregel** bei mehreren blockierenden Kanten: `strong` = die letzte in Kreisrichtung ab dem Scheitelpunkt (Cunningham; hält die Basis **stark zulässig**: von jedem Knoten lässt sich positiver Fluss zur Wurzel schicken, also zeigt jede Baumkante mit Fluss 0
zur Wurzel hin und jede volle von ihr weg; das verhindert Stillstand in Zyklen) gegen `first` = die erste.

Alles ist ganzzahlig; Aufwand in Kantenoperationen (geprüfte Kanten der Preissuche, Kreis-Schritte, aktualisierte Knoten), nie Sekunden: Pivotzahlen sind auf allen Plattformen dieselben.
"""

from dataclasses import dataclass
from math import isqrt

PRICING = ("dantzig", "first", "block")
LEAVING = ("strong", "first")


@dataclass(frozen=True)
class Pivot:
    entering: int          # eintretende Kante (Index in der Kantenliste inkl. künstlicher Kanten)
    direction: int         # +1: Fluss auf der Kante steigt, -1: fällt
    leaving: int           # austretende Kante (gleich `entering`: die Kante wechselt nur ihre Schranke)
    theta: int             # Schritt
    reduced: int           # reduzierte Kosten der eintretenden Kante vor dem Pivot
    cost_after: int        # Kosten der Basislösung nach dem Pivot (einschließlich künstlicher Kanten)
    cycle: tuple           # ((Kante, in Kreisrichtung), ...) ab dem Scheitelpunkt
    examined: int          # in der Preissuche angesehene Kanten
    cycle_steps: int       # Kanten des Kreises (Baumschritte für Scheitelpunkt und Schrittweite)
    updated: int           # Knoten mit neuen Tiefen und Potenzialen
    flow: tuple            # Fluss je Kante nach dem Pivot
    state: tuple           # 'T' Baum, 'L' unten, 'U' oben je Kante nach dem Pivot
    potentials: tuple      # Potenziale je Knoten (ohne Wurzel) nach dem Pivot
    strong_ok: bool        # ist die Basis nach dem Pivot stark zulässig?

    @property
    def degenerate(self):
        return self.theta == 0


@dataclass(frozen=True)
class Result:
    pivots: tuple
    flow: tuple               # Fluss je echter Kante
    cost: int                 # Kosten der echten Kanten
    artificial_flow: int      # Fluss auf künstlichen Kanten (0: zulässig)
    feasible: bool
    optimal: bool             # Optimalitätsbedingung erfüllt (auch bei künstlichem Fluss)
    potentials: tuple         # Potenziale je echtem Knoten
    reduced: tuple            # reduzierte Kosten je Kante (echte, dann künstliche)
    state: tuple              # 'T'/'L'/'U' je Kante (echte, dann künstliche)
    hit_limit: bool
    examined: int             # Preissuche insgesamt (einschließlich der letzten, vergeblichen)
    cycle_steps: int
    updated: int
    final_examined: int       # die letzte, vergebliche Preissuche (der Beweis)
    start_flow: tuple         # Fluss je Kante vor dem ersten Pivot
    big_m: int
    pricing: str
    leaving: str
    n_real: int
    start_state: tuple = ()
    start_potentials: tuple = ()

    @property
    def n_pivots(self):
        return len(self.pivots)

    @property
    def degenerate(self):
        return sum(1 for p in self.pivots if p.degenerate)

    @property
    def effort(self):
        return self.examined + self.cycle_steps + self.updated

    def longest_stall(self):
        best = run = 0
        for p in self.pivots:
            run = run + 1 if p.degenerate else 0
            best = max(best, run)
        return best

    def strong_violations(self):
        return sum(1 for p in self.pivots if not p.strong_ok)


def default_big_m(arcs, n):
    """Ein sicheres M: größer als jeder einfache Weg im Netz kosten kann (n mal die größte Kantenkosten) plus 1. Gilt für Kosten >= 0 (der Bereich der Demo); mit negativen Kosten reicht es nicht."""
    return 1 + n * max((c for _u, _v, _cap, c in arcs), default=1)


def solve(n, arcs, supply, pricing="dantzig", leaving="strong", big_m=None, block=None, max_pivots=None, trace=True):
    """Netzwerksimplex. `arcs`: ((von, nach, Kapazität, Kosten), ...) auf den Knoten 0 .. n-1, `supply[v]`: Bilanz (Überschuss > 0, Bedarf < 0, Summe 0). Rückgabe `Result`."""
    assert pricing in PRICING and leaving in LEAVING and sum(supply) == 0
    m = len(arcs)
    root = n
    big_m = default_big_m(arcs, n) if big_m is None else big_m
    inf = sum(abs(b) for b in supply) + 1
    tail = [a[0] for a in arcs]
    head = [a[1] for a in arcs]
    cap = [a[2] for a in arcs]
    cost = [a[3] for a in arcs]
    flow = [0] * m
    state = ["L"] * m
    parent = [root] * (n + 1)
    pred = [-1] * (n + 1)
    depth = [1] * (n + 1)
    depth[root] = 0
    parent[root] = -1
    pi = [0] * (n + 1)
    children = [[] for _ in range(n + 1)]
    for v in range(n):
        b = supply[v]
        if b >= 0:                                      # Überschuss (oder Bilanz 0, Fluss 0) geht zur Wurzel: Kante zeigt zur Wurzel hin
            tail.append(v); head.append(root)
            flow.append(b)
            pi[v] = -big_m
        else:                                           # Bedarf kommt von der Wurzel
            tail.append(root); head.append(v)
            flow.append(-b)
            pi[v] = big_m
        cap.append(inf)
        cost.append(big_m)
        state.append("T")
        pred[v] = m + v
        children[root].append(v)
    total = m + n
    start_flow = tuple(flow)
    start_state = tuple(state)
    start_pot = tuple(pi[:n])
    max_pivots = max_pivots or 200 * total
    block = block or max(1, isqrt(total))

    def reduced(a):
        return cost[a] + pi[tail[a]] - pi[head[a]]

    def violation(a):
        """Größe der Verletzung und Richtung (+1: Fluss erhöhen, -1: senken); (0, 0) wenn die Kante die Bedingung erfüllt."""
        st = state[a]
        if st == "L":
            r = reduced(a)
            return (-r, 1) if r < 0 else (0, 0)
        if st == "U":
            r = reduced(a)
            return (r, -1) if r > 0 else (0, 0)
        return (0, 0)

    pos = 0

    def price():
        """Wählt die eintretende Kante; Rückgabe (Kante oder None, Richtung, angesehene Kanten)."""
        nonlocal pos
        examined = 0
        if pricing == "dantzig":
            best, best_v, best_d = None, 0, 0
            for a in range(total):
                examined += 1
                v, d = violation(a)
                if v > best_v:
                    best, best_v, best_d = a, v, d
            return best, best_d, examined
        if pricing == "first":
            for k in range(total):
                a = (pos + k) % total
                examined += 1
                v, d = violation(a)
                if v > 0:
                    pos = (a + 1) % total
                    return a, d, examined
            return None, 0, examined
        best, best_v, best_d = None, 0, 0                # block
        start = pos
        blocks = -(-total // block)
        for b in range(blocks):
            lo = (start + b * block) % total
            for k in range(block):
                a = (lo + k) % total
                examined += 1
                v, d = violation(a)
                if v > best_v:
                    best, best_v, best_d = a, v, d
            if best is not None:
                pos = (lo + block) % total
                return best, best_d, examined
        return None, 0, examined

    def strongly_feasible():
        for v in range(n):
            a = pred[v]
            par_to_child = tail[a] == parent[v]
            if flow[a] == 0 and par_to_child:                    # Kante ohne Fluss muss zur Wurzel hin zeigen (dort lässt sich Fluss zur Wurzel schicken)
                return False
            if flow[a] == cap[a] and not par_to_child:           # volle Kante muss von der Wurzel weg zeigen (dort lässt sich Fluss zurücknehmen)
                return False
        return True

    def in_subtree(z, c):
        while depth[z] > depth[c]:
            z = parent[z]
        return z == c

    pivots = []
    examined_total = steps_total = updated_total = 0
    current_cost = sum(flow[a] * cost[a] for a in range(total))
    final_examined = 0
    hit_limit = False
    while True:
        e, direction, examined = price()
        examined_total += examined
        if e is None:
            final_examined = examined
            break
        if len(pivots) >= max_pivots:
            hit_limit = True
            break
        r_e = reduced(e)
        a_node, b_node = (tail[e], head[e]) if direction == 1 else (head[e], tail[e])
        path_a, path_b = [a_node], [b_node]
        x, y = a_node, b_node
        while x != y:
            if depth[x] >= depth[y]:
                x = parent[x]
                path_a.append(x)
            else:
                y = parent[y]
                path_b.append(y)
        # path_a endet im Scheitelpunkt, path_b bis unterhalb; beide gemeinsam bis zum Scheitelpunkt
        apex = path_a[-1]
        while path_b[-1] != apex:
            path_b.append(parent[path_b[-1]])
        cycle = []
        for i in range(len(path_a) - 1, 0, -1):              # Scheitelpunkt -> a: Elternknoten -> Kind
            child, par = path_a[i - 1], path_a[i]
            arc = pred[child]
            cycle.append((arc, tail[arc] == par))
        cycle.append((e, direction == 1))
        for i in range(len(path_b) - 1):                     # b -> Scheitelpunkt: Kind -> Elternknoten
            child = path_b[i]
            arc = pred[child]
            cycle.append((arc, tail[arc] == child))
        limits = [(cap[a] - flow[a]) if fwd else flow[a] for a, fwd in cycle]
        theta = min(limits)
        blocking = [i for i, lim in enumerate(limits) if lim == theta]
        idx = blocking[-1] if leaving == "strong" else blocking[0]
        l_arc, l_fwd = cycle[idx]
        for a, fwd in cycle:
            flow[a] += theta if fwd else -theta
        current_cost -= abs(r_e) * theta
        updated = 0
        if l_arc == e:
            state[e] = "U" if direction == 1 else "L"
        else:
            # austretende Kante: das untere Ende c (pred[c] == l_arc) samt Teilbaum wird abgetrennt und über e neu eingehängt
            c = tail[l_arc] if pred[tail[l_arc]] == l_arc and parent[tail[l_arc]] == head[l_arc] else head[l_arc]
            p = parent[c]
            xe, ye = (tail[e], head[e]) if in_subtree(tail[e], c) else (head[e], tail[e])
            path = [xe]
            while path[-1] != c:
                path.append(parent[path[-1]])
            old_pred = [pred[z] for z in path]
            children[p].remove(c)
            for i in range(1, len(path)):
                children[path[i]].remove(path[i - 1])
                children[path[i - 1]].append(path[i])
            parent[xe], pred[xe] = ye, e
            children[ye].append(xe)
            for i in range(1, len(path)):
                parent[path[i]], pred[path[i]] = path[i - 1], old_pred[i - 1]
            state[e] = "T"
            state[l_arc] = "L" if flow[l_arc] == 0 else "U"
            stack = [xe]
            while stack:
                z = stack.pop()
                par, arc = parent[z], pred[z]
                depth[z] = depth[par] + 1
                pi[z] = pi[par] + cost[arc] if tail[arc] == par else pi[par] - cost[arc]
                updated += 1
                stack.extend(children[z])
        steps_total += len(cycle)
        updated_total += updated
        pivots.append(Pivot(e, direction, l_arc, theta, r_e, current_cost, tuple(cycle), examined, len(cycle), updated,
                            tuple(flow) if trace else (), tuple(state) if trace else (), tuple(pi[:n]) if trace else (), strongly_feasible()))
    art_flow = sum(flow[m:])
    optimal = not hit_limit
    reduced_all = tuple(reduced(a) for a in range(total))
    real_cost = sum(flow[a] * cost[a] for a in range(m))
    return Result(tuple(pivots), tuple(flow[:m]), real_cost, art_flow, optimal and art_flow == 0, optimal, tuple(pi[:n]), reduced_all, tuple(state), hit_limit,
                  examined_total, steps_total, updated_total, final_examined, start_flow, big_m, pricing, leaving, m, start_state, start_pot)


def solve_net(net, value, **kw):
    """Netzwerksimplex für das Flussnetz `net` (Quelle net.s, Senke net.t) mit Flusswert `value`: Bilanz S = +value, T = -value."""
    supply = [0] * net.n
    supply[net.s] = value
    supply[net.t] = -value
    arcs = tuple((u, v, c, k) for u, v, c, k, _kind in net.arcs)
    return solve(net.n, arcs, supply, **kw)


def certificate(n, arcs, supply, res):
    """Unabhängige Prüfung eines zulässigen Ergebnisses: Schranken, Flusserhaltung, und die Optimalitätsbedingung an allen Nicht-Baum-Kanten (L: c' >= 0, U: c' <= 0; Baumkanten c' = 0). Rückgabe (gültig, Gründe)."""
    problems = []
    balance = [0] * n
    for a, (u, v, c, _k) in enumerate(arcs):
        f = res.flow[a]
        if not 0 <= f <= c:
            problems.append(f"Kante {a}: Fluss {f} außerhalb 0..{c}")
        balance[u] += f
        balance[v] -= f
        r, st = res.reduced[a], res.state[a]
        if st == "T" and r != 0:
            problems.append(f"Baumkante {a}: c' = {r}")
        if st == "L" and (f != 0 or r < 0):
            problems.append(f"Kante {a}: an L mit Fluss {f}, c' = {r}")
        if st == "U" and (f != c or r > 0):
            problems.append(f"Kante {a}: an U mit Fluss {f}, c' = {r}")
    if res.artificial_flow == 0 and balance != list(supply):
        problems.append("Flusserhaltung verletzt")
    return not problems, problems
