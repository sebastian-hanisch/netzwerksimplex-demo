"""Plotly-Abbildungen: die Basis als Baum auf der Karte (mit eintretender, austretender Kante und Kreis), Kostenverlauf über die Pivots, Aufwand je Preisregel, Aufwand gegen Netzgröße, Schattenpreise, Verteilung.
Achsen sind gesperrt (fixedrange), damit Touch-Geräte beim Scrollen nicht zoomen. Karten haben gleichen Maßstab (scaleanchor) mit automatischem Bereich; der Rand kommt über zwei unsichtbare Punkte
(ein fest vorgegebener Bereich wird beim ersten Zeichnen in schmaler Breite eingefroren). Beschriftungen von Kanten sind Annotationen mit heller Hinterlegung."""

from math import hypot

import plotly.graph_objects as go

import nsx_constants as C


def lock_axes(fig):
    fig.update_xaxes(fixedrange=True)
    fig.update_yaxes(fixedrange=True)
    return fig


def _base(fig, height):
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=10, b=10), legend=dict(orientation="h", y=-0.22), plot_bgcolor="rgba(0,0,0,0)")
    return lock_axes(fig)


def _frame(fig, points, height, pad=8):
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    fig.update_xaxes(visible=False, scaleanchor="y", scaleratio=1)
    fig.update_yaxes(visible=False)
    fig.add_trace(go.Scatter(x=[min(xs) - pad, max(xs) + pad], y=[min(ys) - pad, max(ys) + pad], mode="markers", marker=dict(opacity=0), hoverinfo="skip", showlegend=False))
    return _base(fig, height)


def _offsets(net):
    groups = {}
    for k, a in enumerate(net.arcs):
        groups.setdefault((min(a[0], a[1]), max(a[0], a[1])), []).append(k)
    off = {}
    for ks in groups.values():
        for i, k in enumerate(ks):
            off[k] = (i - (len(ks) - 1) / 2) * 3.0
    return off


def _segment(net, k, off):
    u, v = net.arcs[k][0], net.arcs[k][1]
    (x0, y0), (x1, y1) = net.pos[u], net.pos[v]
    length = hypot(x1 - x0, y1 - y0) or 1.0
    nx, ny = (y1 - y0) / length, -(x1 - x0) / length
    o = off[k]
    return x0 + nx * o, y0 + ny * o, x1 + nx * o, y1 + ny * o


def _lines(net, ks, off):
    xs, ys = [], []
    for k in ks:
        x0, y0, x1, y1 = _segment(net, k, off)
        xs += [x0, x1, None]
        ys += [y0, y1, None]
    return xs, ys


def build_map(net, state, potentials, pivot=None, height=480, potentials_shown=None):
    """Die Basis auf der Karte: Baumkanten schwarz, volle Nicht-Baum-Kanten orange, leere grau gepunktet. Mit `pivot`: Kreis blau, eintretende Kante grün (dick), austretende rot (gestrichelt).
    Künstliche Kanten (Index >= Zahl der Netzkanten) werden nicht gezeichnet. Potenziale an den Knoten, wenn das Netz klein genug ist (bis 20 Knoten; sonst im Hover)."""
    fig = go.Figure()
    off = _offsets(net)
    m = net.m
    groups = (("L", "leer (untere Schranke)", C.COLORS["lower"], 1, "dot"), ("U", "voll (obere Schranke)", C.COLORS["upper"], 2.5, "solid"), ("T", "Baumkante", C.COLORS["tree"], 3.5, "solid"))
    for st, name, color, width, dash in groups:
        ks = [k for k in range(m) if state[k] == st]
        if ks:
            xs, ys = _lines(net, ks, off)
            fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", line=dict(color=color, width=width, dash=dash), hoverinfo="skip", name=name))
    hx, hy, ht = [], [], []
    for k in range(m):
        x0, y0, x1, y1 = _segment(net, k, off)
        hx.append((x0 + x1) / 2)
        hy.append((y0 + y1) / 2)
        u, v, c, cost, _kind = net.arcs[k]
        ht.append(f"{net.names[u]} → {net.names[v]}: Kapazität {c}, Kosten {cost}, Status {state[k]}")
    fig.add_trace(go.Scatter(x=hx, y=hy, mode="markers", marker=dict(size=8, opacity=0), hovertext=ht, hoverinfo="text", showlegend=False))
    if pivot is not None:
        cyc = [a for a, _fwd in pivot.cycle if a < m and a != pivot.entering and a != pivot.leaving]
        if cyc:
            xs, ys = _lines(net, cyc, off)
            fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", line=dict(color=C.COLORS["cycle"], width=7), opacity=0.35, hoverinfo="skip", name="Kreis"))
        if pivot.entering < m:
            xs, ys = _lines(net, [pivot.entering], off)
            fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", line=dict(color=C.COLORS["enter"], width=6), hoverinfo="skip", name="eintretend"))
        if pivot.leaving < m and pivot.leaving != pivot.entering:
            xs, ys = _lines(net, [pivot.leaving], off)
            fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", line=dict(color=C.COLORS["leave"], width=6, dash="dash"), hoverinfo="skip", name="austretend"))
    show = net.n <= 20 if potentials_shown is None else potentials_shown
    texts = [(f"{net.labels[v]} π={potentials[v]}" if net.labels[v] else f"π={potentials[v]}") if show else (net.labels[v] or "") for v in range(net.n)]
    fig.add_trace(go.Scatter(x=[p[0] for p in net.pos], y=[p[1] for p in net.pos], mode="markers+text", text=texts, textposition="top center", textfont=dict(size=9),
                             marker=dict(size=7, color=C.COLORS["tree"]), hovertext=[f"{net.names[v]}: Potenzial {potentials[v]}" for v in range(net.n)], hoverinfo="text", showlegend=False))
    return _frame(fig, net.pos, height)


def build_cost_curve(res, current=None, height=300):
    """Kosten der Basislösung (einschließlich der Strafe für künstlichen Fluss) über die Pivots, logarithmisch; flache Stücke = degenerierte Pivots (rote Kreuze)."""
    start = res.big_m * sum(res.start_flow[res.n_real:])
    xs = list(range(len(res.pivots) + 1))
    ys = [max(start, 1)] + [max(p.cost_after, 1) for p in res.pivots]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", line=dict(color=C.COLORS["dantzig"], width=2, shape="hv"), name="Kosten der Basislösung"))
    deg = [i + 1 for i, p in enumerate(res.pivots) if p.degenerate]
    if deg:
        fig.add_trace(go.Scatter(x=deg, y=[ys[i] for i in deg], mode="markers", marker=dict(symbol="x", size=7, color=C.COLORS["leave"]), name="degenerierter Pivot (Schritt 0)"))
    if current is not None:
        fig.add_vline(x=current - 1, line=dict(color="#111", dash="dash"), annotation_text="Bild", annotation_position="top")
    fig.update_xaxes(title="Pivots")
    fig.update_yaxes(title="Kosten (mit Strafe)", type="log")
    return _base(fig, height)


def build_rules(cmp, height=320):
    """Aufwand je Preisregel in Kantenoperationen, gestapelt nach Preissuche, Kreis und Aktualisierung; darüber die Pivotzahl."""
    rules = list(cmp["rules"])
    x = [C.LABELS[r] for r in rules]
    fig = go.Figure()
    for key, name, color in (("examined", "Preissuche (geprüfte Kanten)", "#1f77b4"), ("cycle", "Kreis (Baumschritte)", "#2ca02c"), ("updated", "Aktualisierung (Knoten)", "#ff7f0e")):
        fig.add_trace(go.Bar(x=x, y=[cmp["rules"][r][key] for r in rules], name=name, marker_color=color))
    for r, xi in zip(rules, x):
        fig.add_annotation(x=xi, y=cmp["rules"][r]["effort"], text=f"{cmp['rules'][r]['pivots']} Pivots", showarrow=False, yshift=12, font=dict(size=11))
    fig.update_layout(barmode="stack")
    fig.update_yaxes(title="Kantenoperationen")
    return _base(fig, height)


def build_leaving(cmp, height=280):
    """Pivots und Stillstand je Austrittsregel."""
    keys = list(cmp["leaving"])
    x = [C.LEAVING[k].split(" (")[0] for k in keys]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=x, y=[cmp["leaving"][k]["pivots"] - cmp["leaving"][k]["degenerate"] for k in keys], name="Pivots mit Schritt > 0", marker_color="#2ca02c"))
    fig.add_trace(go.Bar(x=x, y=[cmp["leaving"][k]["degenerate"] for k in keys], name="degenerierte Pivots (Schritt 0)", marker_color="#d62728"))
    fig.update_layout(barmode="stack")
    fig.update_yaxes(title="Pivots")
    return _base(fig, height)


def build_sizes(rows, height=340):
    """Aufwand je Preisregel und für Successive Shortest Paths gegen die Zahl der Knoten (Mittel über feste Netze, doppelt logarithmisch)."""
    fig = go.Figure()
    xs = [r["n"] for r in rows]
    for rule in ("dantzig", "first", "block"):
        fig.add_trace(go.Scatter(x=xs, y=[r["effort"][rule] for r in rows], mode="lines+markers", name=C.LABELS[rule], line=dict(color=C.COLORS[rule], width=2)))
    fig.add_trace(go.Scatter(x=xs, y=[r["scanned"] for r in rows], mode="lines+markers", name="Successive Shortest Paths (gescannte Kanten)", line=dict(color=C.COLORS["ssp"], width=2, dash="dash")))
    fig.update_xaxes(title="Knoten", type="log")
    fig.update_yaxes(title="Kantenoperationen", type="log")
    return _base(fig, height)


def build_pivots_vs_size(rows, height=300):
    """Pivots je Preisregel gegen die Zahl der Knoten, dazu die Runden von Successive Shortest Paths."""
    fig = go.Figure()
    xs = [r["n"] for r in rows]
    for rule in ("dantzig", "first", "block"):
        fig.add_trace(go.Scatter(x=xs, y=[r["pivots"][rule] for r in rows], mode="lines+markers", name=C.LABELS[rule], line=dict(color=C.COLORS[rule], width=2)))
    fig.add_trace(go.Scatter(x=xs, y=[r["rounds"] for r in rows], mode="lines+markers", name="Successive Shortest Paths (Runden)", line=dict(color=C.COLORS["ssp"], width=2, dash="dash")))
    fig.update_xaxes(title="Knoten")
    fig.update_yaxes(title="Pivots bzw. Runden")
    return _base(fig, height)


def build_shadow(rows, height=300):
    """Wert einer weiteren Einheit Kapazität je volle Kante (Schattenpreis = minus reduzierte Kosten)."""
    rows = list(reversed(rows))
    fig = go.Figure(go.Bar(y=[r["label"] for r in rows], x=[r["value"] for r in rows], orientation="h", marker_color="#ff7f0e", text=[str(r["value"]) for r in rows], textposition="auto"))
    fig.update_xaxes(title="Kosten, die eine weitere Einheit Kapazität spart")
    return _base(fig, height)


def build_dist(dist, height=300):
    """Median und Mittel des Aufwands je Preisregel über die festen Netze."""
    rules = ("dantzig", "first", "block")
    x = [C.LABELS[r] for r in rules]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=x, y=[dist[r]["effort_median"] for r in rules], name="Median", marker_color="#1f77b4"))
    fig.add_trace(go.Bar(x=x, y=[dist[r]["effort_mean"] for r in rules], name="Mittel", marker_color="#d62728"))
    fig.update_yaxes(title="Kantenoperationen")
    fig.update_layout(barmode="group")
    return _base(fig, height)
