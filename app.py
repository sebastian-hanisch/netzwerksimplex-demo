"""Netzwerksimplex - was ist ein Pivot, und was kostet er? - interaktive Konzept-Demo
Sebastian Hanisch - Operations Research und Machine Learning

Anders als die Fall-Demos im Portfolio (ein Anwendungsfall, mehrere Verfahren im Vergleich) zeigt diese Demo EIN Verfahren - den Netzwerksimplex - und lässt stattdessen das Beispiel wachsen.
Neues Stück (Stück 19) des Min-Cost-Ast der Netzwerkfluss-Linie der "Konzepte"-Reihe: dasselbe Modell wie Successive Shortest Paths, Cycle-Canceling und Cost Scaling, ein anderer Löser.
Die Fall-Demo `network-flow-demo` wendet denselben Löser auf ein Distributionsnetz mit Lagerhaltung an. Siehe README für die Einordnung.

Lauffähig mit: streamlit run app.py
"""

import time

import streamlit as st

import nsx_constants as C
import nsx_evaluation as ev
import nsx_simplex as sx
from nsx_presets import (
    KEPT,
    apply_preset,
    bounds,
    init_session_state_defaults,
    load_permalink_settings,
    randomize_seed,
    seed_widget,
    sync_query_params,
)
from nsx_visualization import build_cost_curve, build_dist, build_leaving, build_map, build_pivots_vs_size, build_rules, build_shadow, build_sizes

st.set_page_config(page_title="Netzwerksimplex – Sebastian Hanisch", layout="wide")


def _f(x, digits=1):
    return "–" if x is None else f"{x:.{digits}f}".replace(".", ",")


def _int(x):
    return "–" if x is None else f"{int(round(x)):,}".replace(",", " ")


def _pct(x, digits=0):
    return f"{100 * x:.{digits}f} %".replace(".", ",")


@st.cache_resource(show_spinner=False, max_entries=32)
def _analysis(params):
    return ev.analyse(ev.Params(*params))


@st.cache_resource(show_spinner=False, max_entries=32)
def _rules(params):
    return ev.compare_rules(ev.Params(*params))


@st.cache_resource(show_spinner=False, max_entries=32)
def _leaving(params):
    return ev.compare_leaving(ev.Params(*params))


st.title("🌳 Netzwerksimplex – was ist ein Pivot?")
st.markdown(
    """
Successive Shortest Paths füllt Wege auf, Cycle-Canceling löscht negative Kreise, Cost Scaling verfeinert Schranken. Der **Netzwerksimplex** löst dasselbe Min-Cost-Flow-Problem ganz anders: er hält immer eine **Basis** - einen **Spannbaum** der Knoten -
und verbessert sie mit **Pivots**. Zum Baum gehören **Potenziale** (Schattenpreise) und für jede Kante außerhalb des Baums die **reduzierten Kosten**: was ein Lkw mehr auf dieser Kante gegenüber dem Baum kostet.
Ist eine Kante ungünstig verletzt, tritt sie in den Baum ein, schließt mit dem Baumpfad einen **Kreis**, Fluss wandert um diesen Kreis, bis eine Kante an ihre Schranke stößt - die tritt aus. Jeder Pivot ist also ein Cycle-Canceling-Schritt, dessen Kreis von den reduzierten Kosten gewählt wird.
Diese Demo lässt Sie Pivot für Pivot zusehen und misst, was er kostet: welche **Preisregel** die eintretende Kante wählt, was **Degeneration** (Pivots ohne Fortschritt) bedeutet, wozu die **starke Zulässigkeit** dient, was das **Big-M** der Startbasis kann und was die Potenziale über **Kapazität** verraten.
"""
)
st.caption(
    "Anders als die Fall-Demos im Portfolio, die an einem Anwendungsfall mehrere Verfahren vergleichen, zeigt diese Demo - Stück 19 der Netzwerkfluss-Linie der \"Konzepte\"-Reihe, neben Successive Shortest Paths, Cycle-Canceling und Cost Scaling - **ein** Verfahren an einem wachsenden Beispiel. "
    "Die Fall-Demo „Distributionsnetzwerk-Optimierung“ nutzt denselben Löser auf einem Distributionsnetz mit Lagerhaltung, mit FCFS-Baseline und Google OR-Tools als Gegenprobe; hier geht es um den Löser selbst."
)

with st.expander("So funktioniert der Netzwerksimplex", expanded=True):
    st.markdown(
        r"""
1. **Start:** eine künstliche Wurzel $R$ und je Knoten eine künstliche Kante mit Kosten $M$: Überschuss geht zur Wurzel, Bedarf kommt von ihr. Das ist ein zulässiger Baum, teuer, aber er existiert immer (**Big-M**).
2. **Potenziale:** entlang jeder Baumkante $(u,v)$ gilt $\pi_v=\pi_u+c_{uv}$, $\pi_R=0$. **Reduzierte Kosten** einer Kante: $\bar c_{uv}=c_{uv}+\pi_u-\pi_v$ (0 auf Baumkanten).
3. **Optimal**, wenn keine Kante an der unteren Schranke $\bar c<0$ und keine an der oberen $\bar c>0$ hat. Sonst wird eine solche Kante zur **eintretenden Kante** (Preisregel).
4. **Kreis und Schritt:** die eintretende Kante bildet mit dem Baumpfad einen Kreis; Fluss um diesen Kreis erhöhen, bis die erste Kante an ihre Schranke stößt: Schritt $\theta$. Die Kosten sinken um $|\bar c|\,\theta$.
5. **Austritt und Tausch:** die blockierende Kante tritt aus dem Baum, die eintretende ersetzt sie; nur der abgetrennte Teilbaum bekommt neue Potenziale. Ist $\theta=0$, ist der Pivot **degeneriert**: der Baum wechselt, der Fluss nicht.
6. **Stark zulässig:** wählt man bei mehreren blockierenden Kanten die letzte in Kreisrichtung (ab dem Scheitelpunkt), bleibt von jedem Knoten positiver Fluss zur Wurzel möglich - das verhindert, dass Degeneration im Kreis läuft.
        """
    )

st.caption("🎯 Schnellstart – ein Beispiel laden:")
names = list(C.PRESETS.keys())
for row in range(0, len(names), 4):
    preset_cols = st.columns(4)
    for col, name in zip(preset_cols, names[row:row + 4]):
        with col:
            st.button(name, width="stretch", on_click=apply_preset, args=(name,), help=C.PRESET_HELP[name])

st.caption(
    "🔗 Die Adresszeile oben spiegelt Ihre aktuelle Konfiguration wider – einfach kopieren, "
    "um ein Szenario zu teilen."
)

load_permalink_settings()
init_session_state_defaults()

with st.sidebar:
    st.header("⚙️ Einstellungen")
    net_key = st.selectbox("Netz", list(C.NETS), key="net_select", format_func=lambda k: C.NETS[k],
                           help="Ein Distributionsnetz (Werke → Verteilzentren → Filialen, dieselbe Kulisse wie in den Nachbar-Demos), die kleine Raute mit Rücknahme oder eine Zuordnung mit Einheitskapazität, in der viele Pivots keinen Fortschritt bringen.")
    pricing = st.radio("Preisregel", list(C.PRICING), key="pricing_radio", format_func=lambda k: C.PRICING[k],
                       help="Welche verletzte Kante eintritt. Dantzig prüft alle Kanten und nimmt die größte Verletzung; „erste verletzte Kante“ sucht zyklisch ab der letzten Stelle; die Blocksuche prüft Blöcke und nimmt die beste des ersten Blocks mit einer Verletzung.")
    leaving = st.radio("Austrittsregel", list(C.LEAVING), key="leaving_radio", format_func=lambda k: C.LEAVING[k],
                       help="Welche von mehreren blockierenden Kanten austritt. „Stark zulässig“ (Cunningham) wählt die letzte in Kreisrichtung ab dem Scheitelpunkt und erhält die starke Zulässigkeit; die Alternative wählt die erste.")
    big_m = st.radio("Big-M in Prozent des sicheren Werts", list(C.BIG_M_PCTS), key="bigm_radio", horizontal=True,
                     help="M in Prozent von 1 + n mal größte Kosten. Ist M zu klein, lohnt sich der künstliche Fluss und bleibt am Ende stehen: die Demo erkennt das und meldet das Netz als unzulässig (Negativkontrolle).")
    if net_key == "distribution":
        seed_widget("plants_slider")
        plants = st.slider("Werke", *bounds("plants_slider"), key="plants_slider")
        st.session_state[KEPT["plants_slider"]] = plants
        seed_widget("dcs_slider")
        dcs = st.slider("Verteilzentren", *bounds("dcs_slider"), key="dcs_slider")
        st.session_state[KEPT["dcs_slider"]] = dcs
        seed_widget("stores_slider")
        stores = st.slider("Filialen", *bounds("stores_slider"), key="stores_slider")
        st.session_state[KEPT["stores_slider"]] = stores
        seed_widget("flow_slider")
        flow = st.slider("Flusswert [% des maximalen Flusses]", *bounds("flow_slider"), key="flow_slider", step=10, help="Wie viel soll von den Werken zu den Filialen fließen? 100 % ist der größte mögliche Fluss; weniger lässt mehr Freiraum und macht den Fluss billiger je Einheit.")
        st.session_state[KEPT["flow_slider"]] = flow
        seed_widget("seed_input")
        seed = st.number_input("Zufalls-Seed", *bounds("seed_input"), key="seed_input", step=1)
        st.session_state[KEPT["seed_input"]] = seed
        st.button("🎲 Neues Netz generieren", width="stretch", on_click=randomize_seed, help="Würfelt einen neuen Zufalls-Seed (neue Lanes, Kapazitäten und Kosten). Die Verteilungen über 40 feste Netze weiter unten ändern sich dabei nicht.")
    else:
        plants = int(st.session_state.get(KEPT["plants_slider"], C.DEFAULT_PLANTS))
        dcs = int(st.session_state.get(KEPT["dcs_slider"], C.DEFAULT_DCS))
        stores = int(st.session_state.get(KEPT["stores_slider"], C.DEFAULT_STORES))
        flow = int(st.session_state.get(KEPT["flow_slider"], C.DEFAULT_FLOW))
        seed = int(st.session_state.get(KEPT["seed_input"], C.DEFAULT_SEED))
        st.caption("Dieses Netz ist fest - es gibt nichts zu erzeugen. Werke, Verteilzentren, Filialen, Flusswert und Seed gehören zum Distributionsnetz.")

sync_query_params({"net_select": net_key, "pricing_radio": pricing, "leaving_radio": leaving, "bigm_radio": int(big_m), "plants_slider": int(plants), "dcs_slider": int(dcs), "stores_slider": int(stores),
                   "flow_slider": int(flow), "seed_input": int(seed)})

# feste Lehrnetze ignorieren die Zufallsregler: sonst würden gleiche Netze unter verschiedenen Schlüsseln mehrfach berechnet
params = (net_key, int(plants), int(dcs), int(stores), int(flow), pricing, leaving, int(big_m), int(seed))
if net_key != "distribution":
    params = (net_key, C.DEFAULT_PLANTS, C.DEFAULT_DCS, C.DEFAULT_STORES, C.DEFAULT_FLOW, pricing, leaving, int(big_m), C.DEFAULT_SEED)
with st.spinner("Rechne..."):
    a = _analysis(params)
net, res, ref, value = a["net"], a["res"], a["ref"], a["value"]
N = res.n_pivots
m = net.m


def _arc_name(arc):
    return f"künstl. {net.labels[arc - m] or net.names[arc - m]}" if arc >= m else ev.arc_label(net, arc)


# --- Pivot für Pivot --------------------------------------------------------------------------------------------------------------

st.markdown("## 🎯 Pivot für Pivot")
st.markdown(f"Das Netz hat **{net.n} Knoten und {m} Kanten**; verlangt ist ein Fluss von **{_int(value)}** Einheiten (Quelle S nach Senke T), gesucht der billigste.")
if st.session_state.get("nsx_step_owner") != params:
    st.session_state["nsx_step"] = max(1, N // 2)
    st.session_state["nsx_step_owner"] = params
view_slot = st.empty()
if N > 0:
    step_col, play_col = st.columns([5, 2])
    with step_col:
        step = st.slider("Pivot", 1, N, key="nsx_step", help="Die Karte zeigt die Basis VOR dem gewählten Pivot: welche Kante tritt ein (grün), welche aus (rot gestrichelt), der Kreis (blau).") if N > 1 else 1
    with play_col:
        auto_play = st.button("▶️ Abspielen", width="stretch")
else:
    step, auto_play = 0, False
    st.info("Schon die Startbasis ist optimal - es gibt keinen Pivot.")


def _render(k):
    with view_slot.container():
        p, state, pot = ev.step_view(res, k)
        c1, c2 = st.columns([3, 2])
        c1.plotly_chart(build_map(net, state, pot, pivot=p), width="stretch", key=f"map_{k}")
        c2.plotly_chart(build_cost_curve(res, current=k, height=460), width="stretch", key=f"cost_{k}")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Eintretende Kante", _arc_name(p.entering), delta=f"c′ = {_int(p.reduced)}", delta_color="off", help="Diese Kante verletzt die Optimalitätsbedingung: ein Lkw mehr (bzw. weniger) auf ihr kostet, gegen den Baum gerechnet, c′ je Einheit weniger als heute.")
        m2.metric("Austretende Kante", _arc_name(p.leaving), help="Die erste Kante des Kreises, die an ihre Schranke stößt. Ist es die eintretende selbst, wechselt sie nur zwischen unterer und oberer Schranke.")
        m3.metric("Schritt θ", _int(p.theta), delta="degeneriert" if p.degenerate else None, delta_color="off", help="Um so viel wird der Fluss um den Kreis verschoben; 0 heißt degeneriert.")
        m4.metric("Kosten danach", _int(p.cost_after), help="Kosten der Basislösung nach dem Pivot einschließlich der Strafe für künstlichen Fluss.")
        viol = []
        for arc in range(m):
            r = net.arcs[arc][3] + pot[net.arcs[arc][0]] - pot[net.arcs[arc][1]]
            if state[arc] == "L" and r < 0:
                viol.append((-r, ev.arc_label(net, arc), r, "unten"))
            elif state[arc] == "U" and r > 0:
                viol.append((r, ev.arc_label(net, arc), r, "oben"))
        viol.sort(key=lambda x: (-x[0], x[1]))
        if viol:
            st.table({"Verletzte Kanten vor dem Pivot (größte zuerst)": [v[1] for v in viol[:6]], "c′ (Schranke)": [f"{_int(v[2])} ({v[3]})" for v in viol[:6]]})
            st.caption(f"{len(viol)} Kanten sind verletzt; die Preisregel „{C.PRICING[pricing].split(' (')[0]}“ hat {ev.arc_label(net, p.entering) if p.entering < m else _arc_name(p.entering)} gewählt (dabei {p.examined} Kanten angesehen).")


if N > 0:
    if auto_play:
        for k in range(1, N + 1):
            _render(k)
            time.sleep(min(0.4, 6.0 / max(N, 1)))
        step = N
    else:
        _render(step)
st.caption("Baumkanten schwarz, volle Kanten (obere Schranke) orange, leere grau gepunktet; π an den Knoten sind die Potenziale. Rechts der Kostenverlauf: er fällt in Stufen, flache Stücke (rote Kreuze) sind degenerierte Pivots. Die Kosten enthalten am Anfang die Strafe M für den künstlichen Fluss.")

if res.feasible:
    if a["match"]:
        st.success(f"✅ Optimal nach {N} Pivots ({res.degenerate} davon degeneriert): Kosten {_int(res.cost)}; Successive Shortest Paths (Stück 4) findet {_int(ref.total)} in {ref.n_rounds} Runden. Die Optimalitätsbedingung gilt an allen Kanten, auch an den {net.n} künstlichen.")
    else:
        st.error("❌ Die Kosten weichen von Successive Shortest Paths ab - das dürfte nicht passieren.")
else:
    st.warning(f"⚠️ Nach {N} Pivots ist die Basis „optimal“, aber {_int(res.artificial_flow)} Einheiten laufen noch über künstliche Kanten: M = {_int(res.big_m)} ist zu klein (sicher wäre {_int(a['safe_m'])}) - der künstliche Weg ist billiger als die echte Lieferung. Ein zu kleines M täuscht ein Optimum vor; die Demo erkennt es am künstlichen Fluss.")

st.markdown("---")

# --- Preisregeln im Vergleich ------------------------------------------------------------------------------------------------------

st.markdown("## 🎯 Welche Kante soll eintreten? Die Preisregeln")
with st.spinner("Rechne die drei Preisregeln..."):
    cmp = _rules(params)
st.plotly_chart(build_rules(cmp), width="stretch", key="rules_chart")
rules = list(cmp["rules"])
st.table({"Preisregel": [C.LABELS[r] for r in rules], "Pivots": [str(cmp["rules"][r]["pivots"]) for r in rules], "Aufwand": [_int(cmp["rules"][r]["effort"]) for r in rules]})
st.caption(f"Aufwand in **Kantenoperationen**: in der Preissuche angesehene Kanten, Schritte um den Kreis (Scheitelpunkt und Schrittweite) und aktualisierte Knoten des abgetrennten Teilbaums. Gleiches Netz, Austrittsregel „{C.LEAVING[leaving].split(' (')[0]}“. "
           "Die Preisregel ändert nicht das Ergebnis (dieselben Kosten), nur den Weg: Dantzig braucht die wenigsten Pivots, prüft dafür jedes Mal alle Kanten.")

st.markdown("---")

# --- Degeneration ------------------------------------------------------------------------------------------------------------------

st.markdown("## 🎯 Pivots ohne Fortschritt: Degeneration")
d1, d2, d3 = st.columns(3)
d1.metric("Degenerierte Pivots", f"{res.degenerate} von {N}", delta=_pct(res.degenerate / N) if N else None, delta_color="off", help="Pivots mit Schritt 0: der Baum wechselt, der Fluss bleibt.")
d2.metric("Längste Folge", _int(res.longest_stall()), help="Wie viele degenerierte Pivots direkt hintereinander vorkamen.")
d3.metric("Pivots, die künstliche Kanten hinauswerfen", _pct(sum(1 for p in res.pivots if p.leaving >= m) / N) if N else "–", help="Anteil der Pivots, bei denen eine künstliche Kante der Startbasis austritt: der Aufwand des Big-M-Starts.")
with st.spinner("Rechne beide Austrittsregeln..."):
    lv = _leaving(params)
st.plotly_chart(build_leaving(lv), width="stretch", key="leaving_chart")
st.table({"Austrittsregel": [C.LEAVING[k].split(" (")[0] for k in lv["leaving"]], "Pivots": [str(lv["leaving"][k]["pivots"]) for k in lv["leaving"]],
          "Pivots ohne starke Zulässigkeit danach": [str(lv["leaving"][k]["violations"]) for k in lv["leaving"]]})
st.caption("Degeneration ist beim Netzwerksimplex der Normalfall: viele Kanten haben Kapazität, an der der Schritt sofort 0 wird. Die starke Zulässigkeit (die letzte blockierende Kante austreten lassen) hält jede Basis in einem Zustand, aus dem Fluss zur Wurzel fließen kann - sie verhindert das Kreisen, spart aber nicht immer Pivots. "
           "Die Spalte rechts zählt Pivots, nach denen die Basis nicht mehr stark zulässig war: bei der starken Regel immer 0.")

st.markdown("---")

# --- Schattenpreise ----------------------------------------------------------------------------------------------------------------

st.markdown("## 🎯 Schattenpreise: was ist mehr Kapazität wert?")
if not res.feasible:
    st.info("Die Schattenpreise gelten nur für eine zulässige Lösung (künstlicher Fluss 0).")
else:
    shadow = ev.shadow_rows(net, res, value)
    if not shadow:
        st.info("In dieser Lösung ist keine Kante voll ausgelastet - mehr Kapazität würde nichts sparen.")
    else:
        st.plotly_chart(build_shadow(shadow), width="stretch", key="shadow_chart")
        st.table({"Volle Kante": [r["label"] for r in shadow], "Wert einer weiteren Einheit / gerechnet": [f"{_int(r['value'])} / {_int(r['recomputed'])}" for r in shadow]})
        exact = sum(1 for r in shadow if r["exact"])
        st.caption(f"Eine volle Kante hat reduzierte Kosten c′ < 0: eine Einheit mehr Kapazität senkt die Kosten um höchstens |c′|. Die Gegenprobe rechnet das Netz mit Kapazität + 1 neu: bei {exact} von {len(shadow)} Kanten stimmt der Wert genau, sonst liegt die Ersparnis darunter (die Basis ändert sich, der Schattenpreis gilt nur in einem Bereich).")

st.markdown("---")

# --- Experimente -------------------------------------------------------------------------------------------------------------------

st.subheader("🔬 Wie wächst der Aufwand mit dem Netz?")
st.caption("Pivots und Kantenoperationen je Preisregel gegen die Zahl der Knoten (Mittel über 5 feste Distributionsnetze je Größe) und Successive Shortest Paths auf demselben Netz (Runden, gescannte Kanten).")
if st.button("Größen durchrechnen (dauert einige Sekunden)", key="sizes_start"):
    st.session_state["sizes_on"] = True
if st.session_state.get("sizes_on"):
    with st.spinner("Rechne 6 Größen × 5 Netze..."):
        rows = ev.sizes(ev.Params(*params))
    st.plotly_chart(build_sizes(rows), width="stretch", key="sizes_chart")
    st.plotly_chart(build_pivots_vs_size(rows), width="stretch", key="pivots_chart")
    st.table({"Knoten": [str(r["n"]) for r in rows], "Pivots Dantzig / erste / Block": [f"{_f(r['pivots']['dantzig'], 0)} / {_f(r['pivots']['first'], 0)} / {_f(r['pivots']['block'], 0)}" for r in rows]})
    st.table({"Knoten": [str(r["n"]) for r in rows], "Aufwand Block / Successive Shortest Paths": [f"{_int(r['effort']['block'])} / {_int(r['scanned'])}" for r in rows]})
    st.caption("Die Pivotzahl wächst grob mit der Knotenzahl, bei der Dantzig-Regel etwa linear. Der Aufwand hängt stärker von der Preisregel ab als von der Pivotzahl. Successive Shortest Paths ist bei kleinen Netzen billiger, der Netzwerksimplex holt mit der Größe auf.")

st.subheader("🔬 Gilt das in jedem Netz?")
st.caption("40 feste Netze mit den gewählten Größen: Pivots, Aufwand, degenerierter Anteil, Stillstand, Austrittsregeln und die Big-M-Schwelle.")
if st.button("40 Netze durchrechnen (dauert einige Sekunden)", key="dist_start"):
    st.session_state["dist_on"] = True
if st.session_state.get("dist_on"):
    with st.spinner("Rechne 40 Netze × 3 Preisregeln × 2 Austrittsregeln..."):
        dist = ev.distribution(ev.Params(*params))
    st.plotly_chart(build_dist(dist), width="stretch", key="dist_chart")
    rl = ("dantzig", "first", "block")
    st.table({"Preisregel": [C.LABELS[r] for r in rl], "Pivots Median / Mittel": [f"{_f(dist[r]['pivots_median'], 1)} / {_f(dist[r]['pivots_mean'], 1)}" for r in rl]})
    st.table({"Preisregel": [C.LABELS[r] for r in rl], "kleinster Aufwand in": [f"{dist[r]['wins']} von {dist['n']} Netzen" for r in rl]})
    st.table({"Preisregel": [C.LABELS[r] for r in rl], "degenerierter Anteil / längste Folge (Mittel)": [f"{_pct(dist[r]['deg_mean'])} / {_f(dist[r]['stall_mean'], 1)}" for r in rl]})
    st.table({"Preisregel": [C.LABELS[r] for r in rl], "erste Austrittskante: mehr / weniger Pivots": [f"{dist[r]['first_more']} / {dist[r]['first_fewer']} Netze" for r in rl]})
    st.caption(f"Big-M: bei 2 / 5 / 10 % des sicheren Werts findet der Löser in {dist['m_ok'][2]} / {dist['m_ok'][5]} / {dist['m_ok'][10]} von {dist['n']} Netzen eine zulässige Lösung. "
               f"Im Mittel {_pct(dist['artificial_share'])} der Pivots werfen künstliche Kanten hinaus.")

st.markdown("---")

# --- Grenzen -----------------------------------------------------------------------------------------------------------------------

st.subheader("🚧 Wo die Annahmen enden")
st.markdown(
    """
| Annahme | Was passiert, wenn sie verletzt ist - und wer ansetzt |
|---|---|
| **Eine Ware** | Mit mehreren Gütern, die sich Kapazität teilen, gibt es keine Baumbasis mehr; das ist ein LP (Demo „Mehrgüterfluss“), Netzwerksimplex-Varianten (Bündel-Simplex) sind nur erwähnt. |
| **Ganzzahlige Daten** | Der Fluss bleibt ganzzahlig (Netzwerkmatrizen sind total unimodular). Mit gebrochenen Kosten oder Kapazitäten rechnet die Fall-Demo mit Gleitkommazahlen und einer Toleranz. |
| **Baum ohne Thread-Index** | Tiefen und Elternzeiger genügen für die Kreissuche hier; industrielle Implementierungen (LEMON, OR-Tools' Netzwerksimplex-Varianten) halten zusätzlich Thread- und Nachfolger-Indizes für schnellere Teilbaum-Updates. |
| **Aufwand in Kantenoperationen** | Die Einheit ist eine Zählung, keine Uhr; sie gewichtet Preissuche, Kreis und Update gleich. Andere Gewichte können die Reihenfolge der Preisregeln verschieben. |
| **Big-M als Start** | Es gibt Alternativen (Zwei-Phasen-Methode, Startbasis aus einem Vorlösungsfluss); sie sind nur erwähnt. |
| **Ein generiertes Netz** | Ein geschichtetes Distributionsnetz mit erzeugten Kapazitäten und Kosten, keine Fremddaten. |
"""
)
st.caption("Die Netzwerkfluss-Linie ist als Ganzes geplant: die dreizehn Stücke der Hauptlinie, darunter **Netzwerksimplex** (dieses Stück, Stück 19, gebaut) als weiterer Löser des Min-Cost-Flow-Modells neben Successive Shortest Paths, Cycle-Canceling und Cost Scaling, und die Erweiterungen E1, E4 und E5.")

st.markdown("---")

with st.expander("📐 Mathematische Formulierung"):
    st.markdown(
        r"""
**Modell.** Gerichteter Graph $G=(V,E)$, Kosten $c_e\in\mathbb Z$, Kapazität $u_e\in\mathbb N$, Bilanz $b_v$ ($\sum_v b_v=0$; hier $b_S=F$, $b_T=-F$):
$$\min\sum_e c_e x_e\quad\text{u.d.N.}\quad\sum_{e\in\delta^+(v)}x_e-\sum_{e\in\delta^-(v)}x_e=b_v,\quad 0\le x_e\le u_e.$$

**Basis.** Eine Basis ist ein Spannbaum $T$ (mit der künstlichen Wurzel $R$: $|V|+1$ Knoten, $|V|$ Baumkanten). Nicht-Baum-Kanten liegen in $L$ ($x=0$) oder $U$ ($x=u$); der Fluss auf den Baumkanten folgt aus der Flusserhaltung. Potenziale $\pi$ mit $\pi_R=0$ und $\pi_v-\pi_u=c_{uv}$ auf Baumkanten,
reduzierte Kosten $\bar c_{uv}=c_{uv}+\pi_u-\pi_v$. **Optimal** $\iff$ $\bar c_e\ge0$ für $e\in L$ und $\bar c_e\le0$ für $e\in U$ (Komplementarität des LP-Duals mit den Potenzialen als Dualvariablen).

**Pivot.** Eintretende Kante $e$ mit Verletzung; sie schließt mit dem Baumpfad den Kreis $C$ (Orientierung: Flussänderung auf $e$). Schritt $\theta=\min\big(\min_{f\in C^+}(u_f-x_f),\ \min_{f\in C^-}x_f\big)$; Kosten $\Delta=-|\bar c_e|\,\theta$.
Austretend ist eine blockierende Kante; ist $\theta=0$, degenerierter Pivot. **Starke Zulässigkeit** (Cunningham 1976): austretend die *letzte* blockierende Kante in Kreisrichtung ab dem Scheitelpunkt; die Basis bleibt stark zulässig: jede Baumkante mit Fluss 0 zeigt zur Wurzel hin, jede volle von ihr weg. Das schließt Kreisen aus.

**Preisregeln.** Dantzig: $\arg\max|\text{Verletzung}|$ über alle Kanten (Aufwand $|E|$ je Pivot); erste verletzte Kante (zyklisch); Blocksuche (Block $\approx\sqrt{|E|}$, wie in LEMON und Grigoriadis).

**Schattenpreis.** Eine volle Kante hat $\bar c_e\le0$: ein Kapazitätszuwachs um 1 senkt die Kosten um höchstens $|\bar c_e|$ (die Wertfunktion ist konvex und stückweise linear in $u_e$), mit Gleichheit, solange die Basis optimal bleibt.

Implementiert in `nsx_scenario.py` (Netz, Lehrnetze, Zufallsgenerator; Kopie aus ssp-demo), `nsx_ssp.py` und `nsx_edmonds_karp.py` (Kopien, für die Gegenprobe und den Max-Flow), `nsx_simplex.py` (Basis, Preisregeln, Pivot, Trace), `nsx_evaluation.py` (Vergleiche, Größen, Verteilungen, Schattenpreise).
        """
    )

st.markdown("---")

st.caption(
    "Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – "
    "Operations Research und Machine Learning ([Über mich](https://sebastianhanisch.net/ueber-mich.html)). "
    "Mehr zur Reihe: [Netzwerkfluss: vom Max-Flow zum Netzdesign](https://sebastianhanisch.net/konzepte-netzwerkfluss.html)."
)
